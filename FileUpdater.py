from __future__ import with_statement
import os, shutil, sys
from stat import *
from python2to3patch import *

def backup(file_to_backup, add_to_end=True):
    path, file_name = os.path.split(file_to_backup)
    files = os.listdir(path)
    if file_name in files:
        i = 0
        while file_name + '.' + str(i) in files: i += 1
        if add_to_end:
            os.rename(os.path.join(path, file_name), os.path.join(path, file_name + '.' + str(i)))
        else:
            for j in reversed(range(i)):
                os.rename(os.path.join(path, file_name + '.' + str(j)),
                          os.path.join(path, file_name + '.' + str(j +  1)))
            os.rename(os.path.join(path, file_name), os.path.join(path, file_name + '.0'))

def copy_single_file(file_to_copy, path, backup_file=True, skip_links=True):
    if not skip_links or not os.path.islink(os.path.join(path, os.path.split(file_to_copy)[1])):
        if backup_file:
            if os.path.split(file_to_copy)[1] == os.path.split(path)[1]: backup(path)
            else: backup(os.path.join(path, os.path.split(file_to_copy)[1]))
        shutil.copy2(file_to_copy, path)

def get_files_of_name(name, base_path=os.getcwd()):
    rtn = []
    if isinstance(name, str):
        name = name.lower()
        isn = name.__eq__
    elif isinstance(name, type(lambda x:x)):
        isn = name
    else:
        name = [i.lower() for i in name]
        isn = name.__contains__
    for root, dirs, files in os.walk(base_path):
        rtn.extend(os.path.join(root, i) for i in files if isn(i.lower()))
    return list(set(rtn))
    
def replace_files(others, use):
    for cur in others:
        if use != cur:
            copy_single_file(use, cur)

def copy_file(file_to_copy, paths):
    for path in paths:
        if (path != file_to_copy and
            (os.path.abspath(os.path.join(path, os.path.split(file_to_copy)[1])) !=
             os.path.abspath(file_to_copy))):
            copy_single_file(file_to_copy, path)

def are_same(file1, file2, check_contents=True):
    if not check_contents: return os.stat(file1) != os.stat(file2)
    contents1, contents2 = get_contents(file1), get_contents(file2)
    return contents1 == contents2

def get_meaningful_stats(file_name):
    rtn = os.stat(file_name)
    meaningful = (ST_MODE, ST_INO, ST_DEV, ST_NLINK, ST_UID, ST_GID, ST_SIZE, ST_MTIME, ST_CTIME)
    return tuple(rtn[i] for i in meaningful)

def group_by_identity(files, check_contents=True):
    if check_contents: return group_by_contents(files)
    rtn = {}
    extras = []
    for file_name in files:
        stats = get_meaningful_stats(file_name)
        if stats in rtn:
            if are_same(rtn[stats][0], file_name, check_contents):
                rtn[stats].append(file_name)
            else:
                extras.append([file_name])
        else:
            rtn[stats] = [file_name]
    return [[file_name for file_name in rtn[stats]] for stats in rtn] + extras

def get_contents(file_name):
    with open(file_name, 'r') as f:
        return f.read()

def group_by_contents(files):
    rtn = {}
    for file_name in files:
        contents = get_contents(file_name)
        if contents in rtn:
            rtn[contents].append(file_name)
        else:
            rtn[contents] = [file_name]
    return [[file_name for file_name in rtn[contents]] for contents in rtn]

def _cmpfiles(file1, file2):
    for i in range(1, len(file1) - 1):
        if file1[i] < file2[i]: return 1
        elif file1[i] > file2[i]: return -1
    if file1[0] < file2[0]: return -1
    elif file1[0] > file2[0]: return 1
    elif file1[0] == file2[0]: return 0

def ask_update_files(file_name, tag_alongs=[], update_tag_alongs=True, base_path=os.getcwd()):
    if update_tag_alongs and tag_alongs:
        for tag_along in tag_alongs:
            ask_update_files(tag_along)
    files = group_by_identity(get_files_of_name(file_name))
    if tag_alongs: tag_files = [get_files_of_name(file_n) for file_n in tag_alongs]
    else: tag_files = []
    rtn = [(paths[0], os.stat(paths[0])[ST_MTIME], os.stat(paths[0])[ST_SIZE], paths[1:]) for paths in files]
    rtn = sorted_multiversion(rtn, _cmpfiles)
    if len(rtn) > 1:
        i = 0
        use = None
        while i < len(rtn):
            ans = ''
            while ('y' not in ans and 'n' not in ans) or ('y' in ans and 'n' in ans):
                cur = os.path.relpath(rtn[i][0],base_path)
                ans = input('Is the newest file ' + cur + '? ').lower()
            if 'y' in ans:
                use = rtn[i][0]
                break
            i += 1
        if not use: return
        paths = []
        ffiles = []
        for file_group in files:
            paths += [os.path.split(i)[0] for i in file_group]
            ffiles += file_group
        replace_files(ffiles, use)
        for file_to_copy in tag_files:
            if file_to_copy:
                if any(os.path.split(use)[0] == os.path.split(i)[0] for i in file_to_copy):
                    copy_file(os.path.join(os.path.split(use)[0], os.path.split(file_to_copy[0])[1]), paths)
                else:
                    copy_file(file_to_copy[0], paths)
    else:
        paths = []
        for file_group in files:
            paths.extend(os.path.split(i)[0] for i in file_group)
        for file_to_copy in tag_files:
            if file_to_copy:
                copy_file(file_to_copy[0], paths)


def consolidate_file(file_n, show_progress=True):
    #if show_progress: print 'Checking "' + os.path.split(file_n)[1] + '"...'
    i = 0
    if not os.path.exists(file_n + '.' + str(i)): return
    contents = set()
    if show_progress: print('Consolidating "' + os.path.split(file_n)[1] + '"...')
    with open(file_n, 'r') as f:
        contents.add(f.read())
    offset = 0
    while os.path.exists(file_n + '.' + str(i)):
        if show_progress: print('  ' + str(i) + ' (version ' + str(i + offset) + ')')
        with open(file_n + '.' + str(i), 'r') as f:
            cur = f.read()
        if cur in contents:
            os.remove(file_n + '.' + str(i))
            offset -= 1
        elif offset != 0:
            os.remove(file_n + '.' + str(i))
            contents.add(cur)
            with open(file_n + '.' + str(i + offset), 'w') as f:
                f.write(cur)
        i += 1

def consolidate_files(base_path=os.getcwd(), show_progress=True):
    if show_progress: print('Consolidating Files...')
    for root, dirs, files in os.walk(base_path):
        if show_progress: print('Consolidating files in "' + root + '"')
        for file_n in [os.path.join(root, i) for i in files]:
            consolidate_file(file_n, show_progress)
        
    

def cleanup_files(base_path=os.getcwd(), show_progress=True, match=(lambda s: s[-1] == '~'), files=None):
    if files is not None:
        if len(files) == 0:
            print('No files were found.')
        else:
            print('\033[2J\033[0;0H')
            print('The following files were found: ')
            for root in files.keys():
                print('In ' + root + ':')
                for file_name in files[root]:
                    print(file_name)
            do_del = None
            while do_del not in ('all', 'none', 'some'):
                do_del = input('Would you like to delete: (a)ll, (n)one, (s)ome, (q)uit? ').strip().lower()
                if do_del[0] in 'ayns':
                    if do_del[0] in 'ay': do_del = 'all' #all, yes
                    elif do_del[0] == 's': do_del = 'some'
                    elif do_del[0] == 'n': do_del = 'none'
                elif do_del[0] in 'qx':
                     sys.exit(0)
                else:
                    print('Invalid response.')
            if do_del != 'none':
                if show_progress: print('Cleaning Files...') 
                for root in files.keys():
                    if show_progress: print('Cleaning files in "%s"' % root)
                    for i in files[root]:
                        while True:
                            if do_del == 'some': del_file = input('Delete ' + i + '?')
                            if do_del == 'all' or (('y' in del_file.lower() or '1' in del_file) and not ('n' in del_file.lower() or '0' in del_file)):
                                os.remove(os.path.join(root, i))
                                break
                            elif not ('y' in del_file.lower() or '1' in del_file) and ('n' in del_file.lower() or '0' in del_file):
                                break
                            else:
                                print('Invalid response.  Type \'y\' to delete the file')
                                print('and \'n\' to leave the file.')
    else:
        rtn_files = {}
        if show_progress: print('Finding Files...')
        for root, dirs, files in os.walk(base_path):
            if show_progress: print('Finding files in "' + root + '"')
            for i in files:
                if match(i):
                    if root in rtn_files.keys(): rtn_files[root].append(i)
                    else: rtn_files[root] = [i]
        return cleanup_files(base_path, show_progress, match, rtn_files)

def cleanup_more_files(base_path=os.getcwd(), show_progress=True, opts=('log', 'aux', 'out', 'toc', 'bbl', 'blg'), match=(lambda s, e: '.' in s and s[s.rindex('.')+1:] == e)):
    for ext in opts:
        while True:
            do_opt = input('Delete files matching %s? ' % ext)
            if ('y' in do_opt.lower() or '1' in do_opt) and not ('n' in do_opt.lower() or '0' in do_opt):
                cleanup_files(base_path, show_progress, (lambda s: match(s, ext)))
                break
            elif not ('y' in do_opt.lower() or '1' in do_opt) and ('n' in do_opt.lower() or '0' in do_opt):
                break
            elif do_opt.lower() in ('quit', 'exit', 'q', 'x'):
                sys.exit(0)
            else:
                print('Invalid response.  Type \'y\' to delete the files')
                print('of this type and \'n\' to leave the files.')
    

# For compatability with Python 3.x
def sorted_multiversion(iterable, cmp=None, key=None, reverse=False):
    try:
        return sorted(iterable, cmp, key, reverse)
    except (TypeError, NameError):
        if cmp is not None and key is None: key = CmpToKey(cmp)
        return sorted(iterable, key=key, reverse=reverse)

def CmpToKey(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) == -1
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) == 1
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) != 1  
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) != -1
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K
