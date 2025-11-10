#!/usr/bin/env python3
"""file-cleaner 

    finds and removes unnecessary files in the specified directory.
    dry-run by default, use --yes to actually delete.
    no more unnecessary files in github repository.

    tugaep 10.11.2025
"""

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Set


def to_lower(s: str) -> str:
    """convert string to lowercase"""
    return s.lower()


def get_depth(base: Path, target: Path) -> int:
    """calculate depth from base to target"""
    try:
        rel = target.relative_to(base)
        return len(rel.parts)
    except ValueError:
        return 0


class Rules:
    """deletion rules"""
    
    def __init__(self):
        self.name_exact: Set[str] = set()  # exact filename matches
        self.ext_lower: Set[str] = set()   # lowercase extensions (without dot)
        self.regexes: List[re.Pattern] = []  # regex patterns applied to filename
    
    def matches(self, path: Path) -> bool:
        """check if file matches these rules"""
        name = path.name
        
        # exact filename match
        if name in self.name_exact:
            return True
        
        # extension check (files only)
        if path.is_file():
            ext = path.suffix
            if ext and ext[0] == '.':
                ext = ext[1:]
            ext = to_lower(ext)
            if ext and ext in self.ext_lower:
                return True
        
        # regex check
        for pattern in self.regexes:
            if pattern.search(name):
                return True
        
        return False


def make_rules(names: List[str], exts: List[str], patterns: List[str]) -> Rules:
    """create rules object from command line arguments"""
    rules = Rules()
    
    for name in names:
        rules.name_exact.add(name)
    
    for ext in exts:
        ext_lower = to_lower(ext)
        rules.ext_lower.add(ext_lower)
    
    for pattern_str in patterns:
        try:
            rules.regexes.append(re.compile(pattern_str))
        except re.error as e:
            print(f"error: invalid regex \"{pattern_str}\": {e}")
            exit(2)
    
    return rules


def confirm(prompt: str) -> bool:
    """get confirmation from user"""
    response = input(f"{prompt} [y/N]: ").strip().lower()
    return response in ('y', 'yes')


def is_dir_empty(path: Path) -> bool:
    """check if directory is empty"""
    try:
        return not any(path.iterdir())
    except (OSError, PermissionError):
        return False


def find_targets(root: Path, rules: Rules, max_depth: Optional[int] = None) -> List[Path]:
    """find files matching rules in root directory"""
    targets = []
    
    for item in root.rglob('*'):
        try:
            # depth check
            if max_depth is not None:
                depth = get_depth(root, item)
                if depth > max_depth:
                    continue
            
            # file/dir exists?
            if not item.exists():
                continue
            
            # matches rules?
            if rules.matches(item):
                targets.append(item)
                # if directory, don't recurse further
                if item.is_dir():
                    pass
        except (OSError, PermissionError) as e:
            print(f"warning: cannot access {item}: {e}")
            continue
    
    return targets


def remove_empty_dirs(root: Path) -> int:
    """remove empty directories starting from deepest"""
    emptied = 0
    dirs = []
    
    # collect all directories
    for item in root.rglob('*'):
        try:
            if item.is_dir():
                dirs.append(item)
        except (OSError, PermissionError):
            continue
    
    # start from longest path (deepest)
    dirs.sort(key=lambda p: len(str(p)), reverse=True)
    
    for d in dirs:
        try:
            if is_dir_empty(d) and d != root:
                d.rmdir()
                emptied += 1
                print(f"removed empty dir {d}")
        except (OSError, PermissionError):
            pass
    
    return emptied


def main():
    """main function - handle command line arguments and run cleanup"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='file-cleaner - find and remove junk files',
        epilog="""
defaults:
  names: __pycache__, .DS_Store
  exts:  log, tmp

notes:
  - dry-run by default. use --yes to actually delete.
  - patterns are regex applied to filename only.
  - --max-depth 0 means only the root directory.

examples:
  file-cleaner .
  file-cleaner . --yes
  file-cleaner . --yes --no-prompt --remove-empty-dirs
  file-cleaner . --yes --max-depth 3 --ext bak old --pattern ".*~$" --name ".Thumbs.db"
        """
    )
    
    parser.add_argument('path', nargs='?', default='.', 
                       help='directory to clean (default: .)')
    parser.add_argument('--yes', action='store_true',
                       help='actually delete (default: dry-run)')
    parser.add_argument('--no-prompt', action='store_true',
                       help='skip confirmation (use with --yes)')
    parser.add_argument('--remove-empty-dirs', action='store_true',
                       help='remove empty directories after deletion')
    parser.add_argument('--max-depth', type=int, metavar='N',
                       help='maximum depth (0 = root only)')
    parser.add_argument('--ext', action='append', dest='exts', default=[],
                       help='extension to delete (can be used multiple times)')
    parser.add_argument('--pattern', action='append', dest='patterns', default=[],
                       help='filename regex pattern to delete (can be used multiple times)')
    parser.add_argument('--name', action='append', dest='names', default=[],
                       help='exact filename to delete (can be used multiple times)')
    
    args = parser.parse_args()
    
    # defaults
    if not args.names:
        args.names = ['__pycache__', '.DS_Store']
    if not args.exts:
        args.exts = ['log', 'tmp']
    
    root = Path(args.path).resolve()
    
    # check if directory exists
    if not root.exists():
        print(f"error: path does not exist: {root}")
        return 1
    
    if not root.is_dir():
        print(f"error: not a directory: {root}")
        return 1
    
    # create rules
    rules = make_rules(args.names, args.exts, args.patterns)
    
    # find targets
    targets = find_targets(root, rules, args.max_depth)
    
    if not targets:
        print("no matching junk found. you're all clean! for now...")
        return 0
    
    # show found files
    print(f"found {len(targets)} target(s):")
    for t in targets:
        print(f"  {t}")
    
    # deletion
    proceed = args.yes
    if args.yes and not args.no_prompt:
        proceed = confirm("delete the above paths?")
    elif not args.yes:
        print("\ndry-run only. use --yes to delete. add --no-prompt to skip confirmation.")
    
    if proceed:
        removed = 0
        for t in targets:
            try:
                if t.is_dir():
                    # remove directory and contents
                    count = sum(1 for _ in t.rglob('*')) + 1  # including dir itself
                    shutil.rmtree(t)
                    removed += 1
                    print(f"removed dir {t} ({count} item(s))")
                else:
                    # remove file
                    t.unlink()
                    removed += 1
                    print(f"removed file {t}")
            except (OSError, PermissionError) as e:
                print(f"error: failed to remove {t}: {e}")
        
        emptied = 0
        if args.remove_empty_dirs:
            emptied = remove_empty_dirs(root)
            print(f"done. removed {removed} target(s), plus {emptied} empty directorie(s).\n")
            print("you're all clean! for now...")
        else:
            print(f"done. removed {removed} target(s).\n")
            print("you're all clean! for now...")
    
    return 0


if __name__ == "__main__":
    main()

