from __future__ import print_function
import argparse
import sys
if sys.version_info.major < 3:
    import ConfigParser as configparser
else:
    import configparser
import io
import hashlib
import mimetypes
import os.path
import shutil
import subprocess


ROOT_KEY = '<root>'
TYPE_DIR = 'd'
TYPE_FILE = 'f'


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

    
def load_project(project_root, file_exclusions=None, dir_exclusions=None):
    selector = FSSelector()

    if file_exclusions:
        for rel_path in file_exclusions:
            selector.add_file_relpath_to_exclusions(rel_path)

    if dir_exclusions:
        for rel_path in dir_exclusions:
            selector.add_dir_relpath_to_exclusions(rel_path)

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
    if not os.path.isabs(path_ref):
        path_ref = os.path.join(dir_home, path_ref)
    return os.path.normpath(path_ref)


def get_os_path_list_from_config(config, section, option, dir_home):
    path_ref_list = get_conf_strings(config, section, option)
    result = []
    for path_ref in path_ref_list:
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
TAG_DIR_FROM = 'DIR_FROM'
TAG_DIR_TO = 'DIR_TO'
TAG_DIR_REPO = 'DIR_REPO'
TAG_DIR_CACHE = 'DIR_CACHE'
TAG_STATE_FILE_FROM = 'STATE_FILE_FROM'
TAG_STATE_FILE_TO = 'STATE_FILE_TO'
TAG_STATE_FILE_REPO = 'STATE_FILE_REPO'
TAG_UPGRADE_REPORT_FILE = 'UPGRADE_REPORT_FILE'
TAG_DIR_CONFLITS_WORK = 'DIR_CONFLITS_WORK'
TAG_RESOLVED_CONFLICTS_CACHE_FILE = 'RESOLVED_CONFLICTS_CACHE_FILE'
TAG_UPGRADE_CACHE_FILE = 'UPGRADE_CACHE_FILE'

TAG_SANITIZE = 'SANITIZE'
TAG_FILES_REPO_PRIVATE = 'FILES_REPO_PRIVATE'
TAG_DIRS_REPO_PRIVATE = 'DIRS_REPO_PRIVATE'
TAG_DIRS_EXCLUDE_BY_FULL_PATH = 'DIRS_EXCLUDE_BY_FULL_PATH'
TAG_FILES_EXCLUDE_BY_FULL_PATH = 'FILES_EXCLUDE_BY_FULL_PATH'

TAG_COMMANDS = 'COMMANDS'
TAG_CMD_DIRECTORY_ADD = 'DIRECTORY_ADD'
TAG_CMD_DIRECTORY_DELETE = 'DIRECTORY_DELETE'
TAG_CMD_FILE_ADD = 'FILE_ADD'
TAG_CMD_FILE_DELETE = 'FILE_DELETE'
TAG_CMD_FILE_MODIFY = 'FILE_MODIFY'
TAG_CMD_FILE_MODIFY_CONFLICTED = 'FILE_MODIFY_CONFLICTED'
TAG_CMD_RESOLVE_CONFLICT = 'RESOLVE_CONFLICT'


def ensure_repo_sanitized(config):
    print("> Ensure repo sanitized ...")
    repo_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_REPO, DIR_HOME)
    exclusions = []
    exclusions += get_os_path_list_from_config_optional(config, TAG_SANITIZE, TAG_DIRS_EXCLUDE_BY_FULL_PATH, repo_dir)
    exclusions += get_os_path_list_from_config_optional(config, TAG_SANITIZE, TAG_FILES_EXCLUDE_BY_FULL_PATH, repo_dir)
    sanitized = True
    for ex in exclusions:
        if os.path.exists(ex):
            status = "failed, exist - "
            sanitized = False
            print('    {}{}'.format(status, ex))
    if not sanitized:
        print("ABORTED, sanitizing error(s) occured.")
        exit(1)


def sanitize_project(project_root):
    print("> Sanitizing '{}' ...".format(project_root))
    dir_exclusions = get_os_path_list_from_config_optional(config, TAG_SANITIZE, TAG_DIRS_EXCLUDE_BY_FULL_PATH, project_root)
    file_exclusions = get_os_path_list_from_config_optional(config, TAG_SANITIZE, TAG_FILES_EXCLUDE_BY_FULL_PATH, project_root)

    for dir_path in dir_exclusions:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print("    dir  deleted - {}".format(dir_path))

    for file_path in file_exclusions:
        if os.path.exists(file_path):
            os.remove(file_path)
            print("    file deleted - {}".format(file_path))


def load_config(conf_file):
    conf_path = os.path.normpath(os.path.abspath(conf_file))
    config = configparser.RawConfigParser()
    config.read(conf_path)
    global DIR_HOME
    DIR_HOME = os.path.dirname(conf_path)
    return config


def scan_project(scan_root, output, file_exclusions=None, dir_exclusions=None):
    print("> SCAN: {} -> {}".format(scan_root, output))
    project = load_project(scan_root, file_exclusions=file_exclusions, dir_exclusions=dir_exclusions)
    project.write(output)


def gen_states(config):
    ensure_repo_sanitized(config)

    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    state_file_from = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_FROM))
    state_file_to = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_TO))
    state_file_repo = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_REPO))
    dir_from = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_FROM, DIR_HOME)
    dir_to = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_TO, DIR_HOME)
    dir_repo = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_REPO, DIR_HOME)
    repo_file_exclusions = get_conf_strings_optional(config, TAG_SANITIZE, TAG_FILES_REPO_PRIVATE)
    repo_dir_exclusions = get_conf_strings_optional(config, TAG_SANITIZE, TAG_DIRS_REPO_PRIVATE)

    sanitize_project(dir_from)
    sanitize_project(dir_to)

    scan_project(dir_from, state_file_from)
    scan_project(dir_to, state_file_to)
    scan_project(dir_repo, state_file_repo, file_exclusions=repo_file_exclusions, dir_exclusions=repo_dir_exclusions)


def report_projects_diff(project_old, project_new):
    print("> Analyzing changes ...")
    changes = eval_projects_diff(project_old, project_new)
    if not changes:
        print("No changes.")
    else:
        print("Changes are the following:")
        for node in changes:
            print(node)


def report_diff_vendor(config):
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    state_file_from = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_FROM))
    state_file_to = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_TO))

    project_from = load_project_from_state_file(state_file_from)
    project_to = load_project_from_state_file(state_file_to)
    report_projects_diff(project_from, project_to)


def report_diff_repo(config):
    ensure_repo_sanitized(config)

    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    state_file_from = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_FROM))
    state_file_repo = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_REPO))

    project_from = load_project_from_state_file(state_file_from)
    project_repo = load_project_from_state_file(state_file_repo)
    report_projects_diff(project_from, project_repo)


def ensure_only_file_modifications(changes):
    unexpected = []
    for chset in changes:
        if chset.flags == CHANGE_STATUS_ITEM_MODIFIED and chset.item_type == TYPE_FILE:
            continue
        unexpected.append(chset)
    if not unexpected:
        return
    print("ABORTED, due to unexpected repo changes:")
    for chset in unexpected:
        print(chset)
    exit(1)


def lookup_for_conflicts(repo_changes, vendor_changes):
    conflicts = []
    markers = set()
    for chset in repo_changes:
        markers.add(chset.archive_path)
    for chset in vendor_changes:
        if chset.archive_path in markers:
            conflicts.append(chset.archive_path)
    return conflicts


def lookup_for_added_directories(vendor_changes):
    added_dirs = []
    for chset in vendor_changes:
        if chset.flags == CHANGE_STATUS_ITEM_ADDED | CHANGE_STATUS_SEEDING:
            added_dirs.append(chset.archive_path)
    return added_dirs


def lookup_for_deleted_directories(vendor_changes):
    deleted_dirs = []
    for chset in vendor_changes:
        if chset.flags == CHANGE_STATUS_ITEM_DELETED | CHANGE_STATUS_SEEDING:
            deleted_dirs.append(chset.archive_path)
    return deleted_dirs


def lookup_for_simple_modifications(vendor_changes, conflicting_files):
    added_files = []
    deleted_files = []
    modified_files = []

    for chset in vendor_changes:
        if chset.archive_path in conflicting_files:
            continue
        if chset.flags & (CHANGE_STATUS_INHERITED | CHANGE_STATUS_SEEDING):
            continue
        if chset.item_type != TYPE_FILE:
            raise Exception("Unexpected simple modification: '{}'".format(chset))

        if chset.flags == CHANGE_STATUS_ITEM_ADDED:
            added_files.append(chset.archive_path)
        elif chset.flags == CHANGE_STATUS_ITEM_DELETED:
            deleted_files.append(chset.archive_path)
        elif chset.flags == CHANGE_STATUS_ITEM_MODIFIED:
            modified_files.append(chset.archive_path)
        else:
            raise Exception("Unexpected simple modification: '{}'".format(chset))

    return added_files, deleted_files, modified_files


TAG_UPGRADE_REPORT_CONFLICTING_FILES = 'conflicting-files'
TAG_UPGRADE_REPORT_ADDED_DIRECTORIES = 'added-directories'
TAG_UPGRADE_REPORT_DELETED_DIRECTORIES = 'deleted-directories'
TAG_UPGRADE_REPORT_ADDED_FILES = 'added-files'
TAG_UPGRADE_REPORT_DELETED_FILES = 'deleted-files'
TAG_UPGRADE_REPORT_MODIFIED_FILES = 'modified-files'

class UpgradeState:
    def __init__(self, conflicting_files, added_directories, deleted_directories, added_files, deleted_files, modified_files):
        self.conflicting_files = conflicting_files
        self.added_directories = added_directories
        self.deleted_directories = deleted_directories
        self.added_files = added_files
        self.deleted_files = deleted_files
        self.modified_files = modified_files

    def dump(self):
        self._dump_items('CONFLICTS', self.conflicting_files)
        self._dump_items('ADDED DIRECTORIES', self.added_directories)
        self._dump_items('DELETED DIRECTORIES', self.deleted_directories)
        self._dump_items('ADDED FILES', self.added_files)
        self._dump_items('DELETED FILES', self.deleted_files)
        self._dump_items('MODIFIED FILES', self.modified_files)

    def _dump_items(self, title, items):
        print(80 * '-')
        print(title)
        print(80 * '-')
        if not items:
            print("  <NO ITEMS>")
        else:
            for value in items:
                print('    {}'.format(value))

    def write(self, filename):
        with io.open(filename, mode='wt', encoding='utf8') as f:
            f.write(_to_string("{\n"))
            for group_name, items in  [ (TAG_UPGRADE_REPORT_CONFLICTING_FILES, self.conflicting_files),
                                        (TAG_UPGRADE_REPORT_ADDED_DIRECTORIES, self.added_directories),
                                        (TAG_UPGRADE_REPORT_DELETED_DIRECTORIES, self.deleted_directories),
                                        (TAG_UPGRADE_REPORT_ADDED_FILES, self.added_files),
                                        (TAG_UPGRADE_REPORT_DELETED_FILES, self.deleted_files),
                                        (TAG_UPGRADE_REPORT_MODIFIED_FILES, self.modified_files) ]:
                f.writelines([_to_string("    '"), _to_string(group_name), _to_string("' :"), _to_string("\n")])
                f.writelines([_to_string("    ["), _to_string("\n")])
                for item in items:
                    f.writelines([_to_string("        '"), _to_string(item), _to_string("',"), _to_string("\n")])
                f.writelines([_to_string("    ],"), _to_string("\n")])
            f.write(_to_string("}\n"))

    @staticmethod
    def load_from_file(filename):
        data = load_py_data(filename)
        conflicting_files    = data[TAG_UPGRADE_REPORT_CONFLICTING_FILES]
        added_directories    = data[TAG_UPGRADE_REPORT_ADDED_DIRECTORIES]
        deleted_directories  = data[TAG_UPGRADE_REPORT_DELETED_DIRECTORIES]
        added_files          = data[TAG_UPGRADE_REPORT_ADDED_FILES]
        deleted_files        = data[TAG_UPGRADE_REPORT_DELETED_FILES]
        modified_files       = data[TAG_UPGRADE_REPORT_MODIFIED_FILES]

        report = UpgradeState(conflicting_files=conflicting_files, added_directories=added_directories, deleted_directories=deleted_directories,
            added_files=added_files, deleted_files=deleted_files, modified_files=modified_files)
        return report

    def apply_commands(self, cache_file, conflics_cmd=None, add_dir_cmd=None, del_dir_cmd=None, add_file_cmd=None, del_file_cmd=None, modify_file_cmd=None):
        processed_items = set()
        if os.path.exists(cache_file):
            with io.open(cache_file, mode='rt', encoding='utf8') as cache:
                for line in cache.readlines():
                    entry = line.rstrip('\n').strip()
                    if entry:
                        processed_items.add(entry)
    
        for cmd, items in [ (conflics_cmd, self.conflicting_files),
                            (add_dir_cmd, self.added_directories),
                            (del_dir_cmd, self.deleted_directories),
                            (add_file_cmd, self.added_files),
                            (del_file_cmd, self.deleted_files),
                            (modify_file_cmd, self.modified_files) ]:
            if cmd is None:
                continue
            for item in items:
                if item in processed_items:
                    print(80 * '-')
                    print("{} - skipped, already processed".format(item))
                    print(80 * '-')
                    continue
                per_item_cmd = cmd.format(item)
                print("exec: {}".format(per_item_cmd))
                print(80 * '-')
                ret = subprocess.call(per_item_cmd)
                print(80 * '-')
                if ret != 0:
                    print("ABORTED.")
                    exit(1)
                with io.open(cache_file, mode='at', encoding='utf8') as cache:
                    cache.writelines([_to_string(item), _to_string("\n")])


def make_upgrade_report(config):
    print("> Collect upgrade report ...")
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    ensure_repo_sanitized(config)

    report_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_UPGRADE_REPORT_FILE))
    print("> Report file: {}".format(report_file))

    state_file_from = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_FROM))
    state_file_repo = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_REPO))
    state_file_to = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_STATE_FILE_TO))

    project_from = load_project_from_state_file(state_file_from)
    project_to = load_project_from_state_file(state_file_to)
    project_repo = load_project_from_state_file(state_file_repo)

    repo_changes = eval_projects_diff(project_from, project_repo)
    ensure_only_file_modifications(repo_changes)

    vendor_changes = eval_projects_diff(project_from, project_to)

    conflicting_files = lookup_for_conflicts(repo_changes, vendor_changes)
    added_directories = lookup_for_added_directories(vendor_changes)
    deleted_directories = lookup_for_deleted_directories(vendor_changes)
    added_files, deleted_files, modified_files = lookup_for_simple_modifications(vendor_changes, conflicting_files)

    report = UpgradeState(conflicting_files=conflicting_files, added_directories=added_directories, deleted_directories=deleted_directories,
        added_files=added_files, deleted_files=deleted_files, modified_files=modified_files)

    report.write(report_file)
    report.dump()


def resolve_conflits(config):
    print("> Started conflits resolving ...")
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    ensure_repo_sanitized(config)
    report_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_UPGRADE_REPORT_FILE))
    executor = UpgradeState.load_from_file(report_file)
    print("> Using report file: {}".format(report_file))

    resolve_conflict_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_RESOLVE_CONFLICT)

    dir_vendor_old = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_FROM, DIR_HOME)
    dir_vendor_new = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_TO, DIR_HOME)
    dir_repo = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_REPO, DIR_HOME)
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    conflicts_cache_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_RESOLVED_CONFLICTS_CACHE_FILE))
    conflicts_work_dir = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_DIR_CONFLITS_WORK))
    print("> Using cache file: {}".format(conflicts_cache_file))
    print("> Conflicts work directory: {}".format(conflicts_work_dir))

    if not os.path.exists(conflicts_work_dir):
        os.makedirs(conflicts_work_dir)

    cmdkw = {'executable': sys.executable, 'dir-here': DIR_HOME, 'dir-vendor-from': dir_vendor_old, 'dir-vendor-to': dir_vendor_new,
        'dir-repo': dir_repo, 'dir-work': conflicts_work_dir}

    resolve_conflict_cmd = resolve_conflict_cmd.format(**cmdkw)
    executor.apply_commands(cache_file=conflicts_cache_file, conflics_cmd=resolve_conflict_cmd)

    print('> Conflicts resolving completed')


def do_upgrade(config):
    print("> Upgrade started ...")
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    ensure_repo_sanitized(config)
    report_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_UPGRADE_REPORT_FILE))
    executor = UpgradeState.load_from_file(report_file)
    print("> Using report file: {}".format(report_file))

    add_dir_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_DIRECTORY_ADD)
    del_dir_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_DIRECTORY_DELETE)
    add_file_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_FILE_ADD)
    del_file_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_FILE_DELETE)
    modify_file_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_FILE_MODIFY)
    resolved_conflict_cmd = get_conf_string1(config, TAG_COMMANDS, TAG_CMD_FILE_MODIFY_CONFLICTED)

    conflicts_work_dir = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_DIR_CONFLITS_WORK))
    dir_vendor_new = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_TO, DIR_HOME)
    dir_repo = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_REPO, DIR_HOME)
    cache_dir = get_os_path_from_config(config, TAG_CONFIG, TAG_DIR_CACHE, DIR_HOME)
    upgrade_cache_file = os.path.join(cache_dir, get_conf_string1(config, TAG_CONFIG, TAG_UPGRADE_CACHE_FILE))
    print("> Using cache file: {}".format(upgrade_cache_file))

    cmdkw = {'executable': sys.executable, 'dir-here': DIR_HOME, 'dir-conflicts': conflicts_work_dir, 'dir-from': dir_vendor_new, 'dir-to': dir_repo}
    resolved_conflict_cmd = resolved_conflict_cmd.format(**cmdkw)
    add_dir_cmd = add_dir_cmd.format(**cmdkw)
    del_dir_cmd = del_dir_cmd.format(**cmdkw)
    add_file_cmd = add_file_cmd.format(**cmdkw)
    del_file_cmd = del_file_cmd.format(**cmdkw)
    modify_file_cmd = modify_file_cmd.format(**cmdkw)
    
    executor.apply_commands(cache_file=upgrade_cache_file,
        conflics_cmd=resolved_conflict_cmd,
        add_dir_cmd=add_dir_cmd, del_dir_cmd=del_dir_cmd,
        add_file_cmd=add_file_cmd, del_file_cmd=del_file_cmd, modify_file_cmd=modify_file_cmd)

    print('> Upgrade completed')


# ============================================================================================================================
# ============================================================================================================================
# ============================================================================================================================


TAG_RUN_MODE_INIT = 'init'
TAG_RUN_MODE_DIFF_VENDOR = 'diff-vendor'
TAG_RUN_MODE_DIFF_REPO = 'diff-repo'
TAG_RUN_MODE_UPGRADE_REPORT = 'make-upgrade-report'
TAG_RUN_MODE_UPGRADE = 'upgrade'
TAG_RUN_MODE_RESOLVE_CONFLITS = 'resolve-conflicts'


RUN_MODES = [
  TAG_RUN_MODE_INIT,
  TAG_RUN_MODE_DIFF_VENDOR,
  TAG_RUN_MODE_DIFF_REPO,
  TAG_RUN_MODE_UPGRADE_REPORT,
  TAG_RUN_MODE_RESOLVE_CONFLITS,
  TAG_RUN_MODE_UPGRADE,
]

RUN_MAPPING = {
  TAG_RUN_MODE_INIT: gen_states,
  TAG_RUN_MODE_DIFF_VENDOR: report_diff_vendor,
  TAG_RUN_MODE_DIFF_REPO: report_diff_repo,
  TAG_RUN_MODE_UPGRADE_REPORT: make_upgrade_report,
  TAG_RUN_MODE_RESOLVE_CONFLITS: resolve_conflits,
  TAG_RUN_MODE_UPGRADE: do_upgrade,
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--mode', required=True, choices=RUN_MODES)
    args = parser.parse_args()
    config = load_config(args.config)
    run_func = RUN_MAPPING[args.mode]
    run_func(config)
