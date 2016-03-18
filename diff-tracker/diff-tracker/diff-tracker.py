import sys
if sys.version_info[0] < 3:
    import ConfigParser as configparser
else:
    import configparser
import argparse
import io
import hashlib
import mimetypes
import os.path
import shutil
import subprocess


ROOT_KEY = '<root>'
TYPE_DIR = 'd'
TYPE_FILE = 'f'
TYPE_SYMLINK = 's'

CHANGE_STATUS_ITEM_MODIFIED = 0x0001
CHANGE_STATUS_ITEM_ADDED    = 0x0002
CHANGE_STATUS_ITEM_DELETED  = 0x0004
CHANGE_STATUS_SEEDING       = 0x0008
CHANGE_STATUS_INHERITED     = 0x0010


def _to_string(v):
    if sys.version_info[0] < 3:
        if isinstance(v, unicode):
            return v
        return unicode(v)
    else:
        if isinstance(v, str):
            return v
        return str(v)


def _from_string(v):
    if sys.version_info[0] < 3:
        return v
    return v.encode('utf-8')


def is_item_type_recursive(tp_name):
    return (tp_name == TYPE_DIR)


class FileTreeNode:
    def __init__(self, local_id, parent_key = None):
        self.local_id = id
        if (parent_key is None) or (parent_key == ROOT_KEY):
            self.node_key = local_id
        else:
            self.node_key = '/'.join([parent_key, local_id])
        self.children = {}

    def get_child(self, id):
        ret = self.children.get(id)
        if ret is None:
            raise Exception("Node '{}' doesn't have child named '{}'.".format(self.id, id))
        return ret

    def add_child(self, id):
        if id in self.children:
            raise Exception("Child named '{}' already added in node '{}'.".format(id, self.id))
        self.children[id] = FileTreeNode(id, self.node_key)

    def select_keys_of_children(self):
        ret = set()
        for k in sorted(self.children.keys()):
            c = self.children[k]
            ret.add(c.node_key)
        return ret


def mkfs(nodes):
    root = FileTreeNode(ROOT_KEY)
    for key in sorted(nodes.keys()):
        if key == ROOT_KEY:
            continue
        _a, _b, _c = key.rpartition('/')
        parent = root
        subject = _c
        if _a:
            for bit in _a.split('/'):
                parent = parent.get_child(bit)
        parent.add_child(subject)
    return root


class ProjectState:
    def __init__(self, nodes):
        if not nodes:
            nodes = {}
            nodes[ROOT_KEY] = Source(ROOT_KEY, TYPE_DIR, hashlib.md5().hexdigest())
        self.nodes = nodes
        self.fs = mkfs(nodes)

    def write(self, filename):
        with io.open(filename, mode='wt', encoding='utf8') as f:
            f.write(_to_string('{\n'))
            for k in sorted(self.nodes.keys()):
                f.writelines([_to_string(self.nodes[k]), _to_string('\n')])
            f.write(_to_string('}\n'))

    def _fs_resolve(self, key):
        if key == ROOT_KEY:
            return self.fs
        bits = key.split('/')
        ret = self.fs
        for b in bits:
            ret = ret.get_child(b)
        return ret

    def select_keys_of_children(self, parent_key):
        fs_node = self._fs_resolve(parent_key)
        return fs_node.select_keys_of_children()


class Source:
    def __init__(self, archive_path, src_type, digest):
        self.archive_path = archive_path
        self.src_type = src_type
        self.digest = digest

    def __str__(self):
        return "    '{}' : ('{}', '{}'),".format(self.archive_path, self.src_type, self.digest)


class FSSelector:
    def __init__(self):
        self._dir_names_to_exclude = set()
        self._dir_relpaths_to_exclude = set()
        self._file_names_to_exclude = set()
        self._file_relpaths_to_exclude = set()

    def add_dir_name_to_exclusions(self, dname):
        self._dir_names_to_exclude.add(dname)

    def add_dir_relpath_to_exclusions(self, relpath):
        self._dir_relpaths_to_exclude.add(relpath)

    def add_file_name_to_exclusions(self, fname):
        self._file_names_to_exclude.add(fname)

    def add_file_relpath_to_exclusions(self, relpath):
        self._file_relpaths_to_exclude.add(relpath)

    def dir_in_interest(self, dname, relpath):
        if dname in self._dir_names_to_exclude:
            return False
        if relpath in self._dir_relpaths_to_exclude:
            return False
        return True

    def file_in_interest(self, fname, relpath):
        if fname in self._file_names_to_exclude:
            return False
        if relpath in self._file_relpaths_to_exclude:
            return False
        return True


def make_rel_path(bits, tail):
    parts = bits[:]
    parts.append(tail)
    return '/'.join(parts)


def md5_of_file(path):
    m = hashlib.md5()
    data = io.FileIO(path).readall().replace(b'\r\n', b'\n').rstrip(b'\r\n')
    m.update(data)
    return m.hexdigest()


def md5_of_string(value):
    m = hashlib.md5()
    m.update(_from_string(value))
    return m.hexdigest()


def enum_fs_content_recursive(seed, selector, outbox, pathbits):
    if pathbits:
        fs_path = os.path.join(seed, *pathbits)
        if len(pathbits) > 1:
            parent = '/'.join(pathbits[0:-1])
        else:
            parent = ROOT_KEY
    else:
        fs_path = seed
        parent = None

    if os.path.islink(fs_path):
        arch_path = '/'.join(pathbits)
        link_value = os.readlink(fs_path)
        fsum = md5_of_string(link_value)
        item = Source(arch_path, TYPE_SYMLINK, fsum)
        outbox[arch_path] = item
        return fsum

    is_dir = os.path.isdir(fs_path)
    if not is_dir:
        arch_path = '/'.join(pathbits)
        fsum = md5_of_file(fs_path)
        item = Source(arch_path, TYPE_FILE, fsum)
        outbox[arch_path] = item
        return fsum

    files = []
    dirs = []
    for name in os.listdir(fs_path):
        p = os.path.join(fs_path, name)
        if os.path.isdir(p):
            dirs.append(name)
        else:
            files.append(name)
    dsum = hashlib.md5()
    for name in sorted(files):
        rel_path = make_rel_path(pathbits, name)
        if not selector.file_in_interest(name, rel_path):
            continue
        pathbits.append(name)
        s = enum_fs_content_recursive(seed, selector, outbox, pathbits)
        del pathbits[-1]
        dsum.update(s.encode())
    for name in sorted(dirs):
        rel_path = make_rel_path(pathbits, name)
        if not selector.dir_in_interest(name, rel_path):
            continue
        pathbits.append(name)
        s = enum_fs_content_recursive(seed, selector, outbox, pathbits)
        del pathbits[-1]
        dsum.update(s.encode())

    dir_digest = dsum.hexdigest()
    if pathbits:
        arch_path = '/'.join(pathbits)
        item = Source(arch_path, TYPE_DIR, dir_digest)
        outbox[arch_path] = item
    else:
        outbox[ROOT_KEY] = Source(ROOT_KEY, TYPE_DIR, dir_digest)
    return dir_digest


def enum_fs_content(seed, selector):
    pathbits = []
    outbox = {}
    enum_fs_content_recursive(seed, selector, outbox, pathbits)
    return outbox


def load_py_data(filename):
    source = io.open(filename, mode='rt', encoding='utf8').read()
    ast = compile(source, filename, 'eval')
    return eval(ast, {'__builtins__': None}, {})


def load_project(project_root, file_exclusions=None, dir_exclusions=None, fname_exclusions=None, dname_exclusions=None):
    selector = FSSelector()

    if file_exclusions:
        for rel_path in file_exclusions:
            selector.add_file_relpath_to_exclusions(rel_path)

    if dir_exclusions:
        for rel_path in dir_exclusions:
            selector.add_dir_relpath_to_exclusions(rel_path)

    if fname_exclusions:
        for fname in fname_exclusions:
            selector.add_file_name_to_exclusions(fname)

    if dname_exclusions:
        for dname in dname_exclusions:
            selector.add_dir_name_to_exclusions(dname)

    nodes = enum_fs_content(project_root, selector)
    return ProjectState(nodes)


def load_project_from_state_file(state_file):
    nodes = {}
    flat = load_py_data(state_file)
    for k, v in flat.items():
        tpname, digest = v[0], v[1]
        src = Source(k, tpname, digest)
        nodes[k] = src
    return ProjectState(nodes)


class ChangeNode:
    def __init__(self, item_type, archive_path, flags):
        self.item_type = item_type
        self.archive_path = archive_path
        self.flags = flags

    def __str__(self):
        seed_status = ' '
        modification_type = '?'
        if self.flags & CHANGE_STATUS_ITEM_MODIFIED:
            modification_type = 'M'
        elif self.flags & CHANGE_STATUS_ITEM_ADDED:
            modification_type = 'A'
            if self.flags & CHANGE_STATUS_SEEDING:
                seed_status = '*'
            elif self.flags & CHANGE_STATUS_INHERITED:
                seed_status = '+'
        elif self.flags & CHANGE_STATUS_ITEM_DELETED:
            modification_type = 'D'
            if self.flags & CHANGE_STATUS_SEEDING:
                seed_status = '*'
            elif self.flags & CHANGE_STATUS_INHERITED:
                seed_status = '-'
        return '{}   {},{}    {}'.format(seed_status, modification_type, self.item_type, self.archive_path)


class ChangeSet:
    def __init__(self, key):
        self.key = key
        self.changes = []

    def on_deleted(self, src, ctx, is_subcall):
        flags = CHANGE_STATUS_ITEM_DELETED
        item_recursive = is_item_type_recursive(src.src_type)
        if not is_subcall and item_recursive:
            flags |= CHANGE_STATUS_SEEDING
        if is_subcall:
            flags |= CHANGE_STATUS_INHERITED
        node = ChangeNode(src.src_type, src.archive_path, flags)
        self.changes.append(node)
        if item_recursive:
            children = ctx.select_keys_of_children(src.archive_path)
            for child in sorted(children):
                child_src = ctx.nodes[child]
                self.on_deleted(child_src, ctx, True)

    def on_created(self, src, ctx, is_subcall):
        flags = CHANGE_STATUS_ITEM_ADDED
        item_recursive = is_item_type_recursive(src.src_type)
        if not is_subcall and item_recursive:
            flags |= CHANGE_STATUS_SEEDING
        if is_subcall:
            flags |= CHANGE_STATUS_INHERITED
        node = ChangeNode(src.src_type, src.archive_path, flags)
        self.changes.append(node)
        if item_recursive:
            children = ctx.select_keys_of_children(src.archive_path)
            for child in sorted(children):
                child_src = ctx.nodes[child]
                self.on_created(child_src, ctx, True)

    def on_modified(self, prev, now):
        node = ChangeNode(now.src_type, now.archive_path, CHANGE_STATUS_ITEM_MODIFIED)
        self.changes.append(node)


def eval_diff_recursive(key, p, n, outbox):
    src_p = p.nodes.get(key)
    src_n = n.nodes.get(key)

    if (src_p is None) and (src_n is None):
        raise Exception("Unknown item key in diff evalution: '{}'.".format(key))

    if (src_p is None):
        changes = ChangeSet(key)
        changes.on_created(src_n, n, False)
        outbox[key] = changes
        return

    if (src_n is None):
        changes = ChangeSet(key)
        changes.on_deleted(src_p, p, False)
        outbox[key] = changes
        return

    prev_type = src_p.src_type
    prev_digest = src_p.digest

    now_type = src_n.src_type
    now_digest = src_n.digest

    if (now_type != prev_type):
        changes = ChangeSet(key)
        changes.on_deleted(src_p, False)
        changes.on_created(src_n, False)
        outbox[key] = changes
        return
    else:
        node_type = now_type

    if (prev_digest == now_digest):
        return

    if not is_item_type_recursive(node_type):
        changes = ChangeSet(key)
        changes.on_modified(src_p, src_n)
        outbox[key] = changes
        return

    keys_of_children = p.select_keys_of_children(key) | n.select_keys_of_children(key)

    for k in sorted(keys_of_children):
        eval_diff_recursive(k, p, n, outbox)


def eval_projects_diff(prev, now):
    result = []
    changes = {}
    eval_diff_recursive(ROOT_KEY, prev, now, changes)
    for k in sorted(changes.keys()):
        chset = changes[k]
        result += chset.changes
    return result


# ============================================================================================================================
# ============================================================================================================================
# ============================================================================================================================


def get_conf_string1(config, section, option):
    return config.get(section, option).strip()


def get_conf_string0(config, section, option):
    if not config.has_option(section, option):
        return None
    return get_conf_string1(config, section, option)


def get_conf_strings(config, section, option):
    return config.get(section, option).split()


def get_conf_strings_optional(config, section, option):
    if not config.has_option(section, option):
        return []
    return get_conf_strings(config, section, option)


def get_os_path_from_config(config, section, option, dir_home):
    path_ref = get_conf_string1(config, section, option)
    path_ref = os.path.expanduser(path_ref)
    if not os.path.isabs(path_ref):
        path_ref = os.path.join(dir_home, path_ref)
    return os.path.normpath(path_ref)


def get_os_path_list_from_config(config, section, option, dir_home):
    path_ref_list = get_conf_strings(config, section, option)
    result = []
    for path_ref in path_ref_list:
        path_ref = os.path.expanduser(path_ref)
        if not os.path.isabs(path_ref):
            path_ref = os.path.join(dir_home, path_ref)
        result.append(os.path.normpath(path_ref))
    return result


def get_os_path_list_from_config_optional(config, section, option, dir_home):
    if not config.has_option(section, option):
        return []
    return get_os_path_list_from_config(config, section, option, dir_home)


# ============================================================================================================================
# ============================================================================================================================
# ============================================================================================================================


DIR_HOME = None

TAG_CONFIG = 'CONFIG'
TAG_DIR_TRACK_ROOT = 'DIR_TRACK_ROOT'
TAG_DIR_CACHE = 'DIR_CACHE'
TAG_STATE_FILE = 'STATE_FILE'
TAG_DIRS_EXCLUDE_BY_FULL_PATH = 'DIRS_EXCLUDE_BY_FULL_PATH'
TAG_FILES_EXCLUDE_BY_FULL_PATH = 'FILES_EXCLUDE_BY_FULL_PATH'
TAG_DIRS_EXCLUDE_BY_NAME = 'DIRS_EXCLUDE_BY_NAME'
TAG_FILES_EXCLUDE_BY_NAME = 'FILES_EXCLUDE_BY_NAME'


def load_config(conf_file):
    conf_path = os.path.normpath(os.path.abspath(conf_file))
    config = configparser.RawConfigParser()
    config.read(conf_path)
    global DIR_HOME
    DIR_HOME = os.path.dirname(conf_path)
    return config


def scan_project(scan_root, output, file_exclusions=None, dir_exclusions=None, fname_exclusions=None, dname_exclusions=None):
    print("> SCAN: {} -> {}".format(scan_root, output))
    project = load_project(scan_root, file_exclusions=file_exclusions, dir_exclusions=dir_exclusions, fname_exclusions=fname_exclusions, dname_exclusions=dname_exclusions)
    project.write(output)


def gen_state(config):
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    dir_to_track = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_TRACK_ROOT, DIR_HOME)
    state_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE))
    dir_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_DIRS_EXCLUDE_BY_FULL_PATH)
    file_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_FILES_EXCLUDE_BY_FULL_PATH)
    dname_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_DIRS_EXCLUDE_BY_NAME)
    fname_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_FILES_EXCLUDE_BY_NAME)

    scan_project(dir_to_track, state_file,
        dir_exclusions=dir_exclusions, file_exclusions=file_exclusions,
        dname_exclusions=dname_exclusions, fname_exclusions=fname_exclusions)


def report_projects_diff(project_old, project_new):
    print("> Analyzing changes ...")
    changes = eval_projects_diff(project_old, project_new)
    if not changes:
        print("No changes.")
    else:
        print("Changes are the following:")
        for node in changes:
            print(node)


def report_diff(config):
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    dir_to_track = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_TRACK_ROOT, DIR_HOME)
    state_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE))
    dir_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_DIRS_EXCLUDE_BY_FULL_PATH)
    file_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_FILES_EXCLUDE_BY_FULL_PATH)
    dname_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_DIRS_EXCLUDE_BY_NAME)
    fname_exclusions = get_conf_strings_optional(config, TAG_CONFIG, TAG_FILES_EXCLUDE_BY_NAME)

    project_from = load_project_from_state_file(state_file)
    project_to = load_project(dir_to_track, file_exclusions=file_exclusions, dir_exclusions=dir_exclusions, fname_exclusions=fname_exclusions, dname_exclusions=dname_exclusions)
    report_projects_diff(project_from, project_to)


# ============================================================================================================================
# ============================================================================================================================
# ============================================================================================================================


TAG_RUN_MODE_INIT = 'init'
TAG_RUN_MODE_DIFF = 'diff'


RUN_MODES = [
  TAG_RUN_MODE_INIT,
  TAG_RUN_MODE_DIFF,
]

RUN_MAPPING = {
  TAG_RUN_MODE_INIT: gen_state,
  TAG_RUN_MODE_DIFF: report_diff,
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--mode', required=True, choices=RUN_MODES)
    args = parser.parse_args()
    config = load_config(args.config)
    run_func = RUN_MAPPING[args.mode]
    run_func(config)
