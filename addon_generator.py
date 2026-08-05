"""
addons.xml generator
Copyright (C) 2018 Lunatixz
Copyright (C) 2012-2013 Garrett Brown
Copyright (C) 2010 j48antialias

Based on code by j48antialias:
https://anarchintosh-projects.googlecode.com/files/addons_xml_generator.py
"""

import os, sys, datetime, hashlib
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

LOG_FILE = None

def _log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_FILE:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

GITPATH = os.path.dirname(os.path.abspath(__file__))
ZIPPATH = os.path.join(GITPATH, 'zips')
DELETE_EXT = ('.pyc', '.pyo', '.db', '.bak')
DELETE_FOLDERS = {'__pycache__', '.idea', 'Corel Auto-Preserve'}


class Generator:
    """Generates addons.xml and addons.xml.md5 from multiple addon.xml files."""

    def __init__(self):
        global LOG_FILE
        LOG_FILE = os.path.join(GITPATH, 'generator.log')
        _log('=== Generator started ===')
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        self._zipit(GITPATH)
        _log("Finished updating addons xml and md5 files")

    def _clean_addons(self):
        for root, dirnames, filenames in os.walk(GITPATH):
            for dirname in dirnames:
                if dirname in DELETE_FOLDERS:
                    path = os.path.join(root, dirname)
                    try:
                        _log(f"removing: {dirname}")
                        try:
                            os.rmdir(path)
                        except OSError:
                            rmtree(path)
                    except Exception:
                        pass
            for filename in filenames:
                if filename.endswith(DELETE_EXT):
                    _log(f"removing: {filename}")
                    os.remove(os.path.join(root, filename))

    def _generate_addons_file(self):
        addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'

        for addon in os.listdir(GITPATH):
            addon_path = os.path.join(GITPATH, addon, "addon.xml")
            if not os.path.isdir(os.path.join(GITPATH, addon)) or addon in (".svn", ".git"):
                continue
            try:
                with open(addon_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                addon_xml = "".join(line.rstrip() + "\n" for line in lines if "<?xml" not in line)
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception as e:
                _log(f"Excluding {addon_path} for {e}")

        addons_xml = addons_xml.strip() + "\n</addons>\n"
        self._save_file(addons_xml.encode("UTF-8"), "addons.xml")

    def _generate_md5_file(self):
        try:
            with open(os.path.join(GITPATH, "addons.xml"), "r", encoding="UTF-8") as f:
                m = hashlib.md5(f.read().encode("UTF-8")).hexdigest()
            self._save_file(m.encode("UTF-8"), "addons.xml.md5")
        except Exception as e:
            _log(f"An error occurred creating addons.xml.md5 file!\n{e}")

    def _save_file(self, data, filename):
        try:
            with open(os.path.join(GITPATH, filename), "wb") as f:
                f.write(data)
        except Exception as e:
            _log(f"An error occurred saving {filename} file!\n{e}")

    def get_plugin_version(self, addon_dir):
        addon_file = os.path.join(addon_dir, 'addon.xml')
        if not os.path.exists(addon_file):
            return None
        try:
            with open(addon_file, 'r', encoding="utf-8") as f:
                node = xml.etree.ElementTree.XML(f.read())
            return node.get('version')
        except Exception as e:
            _log(f'Failed to open {addon_file}: {e}')
            return None

    def create_zip_file(self, fpath, addon):
        _log(f"addon_dir: {addon}")
        version = self.get_plugin_version(os.path.join(fpath, addon))
        if not version:
            return
        _log(f"version: {version}")

        home = os.getcwd()
        os.chdir(fpath)

        path = os.path.join(ZIPPATH, addon)
        os.makedirs(path, exist_ok=True)

        _log("copying icon.png...")
        if os.path.exists(os.path.join(addon, 'icon.png')):
            copyfile(os.path.join(addon, 'icon.png'), os.path.join(path, 'icon.png'))
        elif os.path.exists(os.path.join(addon, 'resources', 'images', 'icon.png')):
            copyfile(os.path.join(addon, 'resources', 'images', 'icon.png'), os.path.join(path, 'icon.png'))

        _log("copying fanart.jpg...")
        if os.path.exists(os.path.join(addon, 'fanart.jpg')):
            copyfile(os.path.join(addon, 'fanart.jpg'), os.path.join(path, 'fanart.jpg'))
        elif os.path.exists(os.path.join(addon, 'resources', 'images', 'fanart.jpg')):
            copyfile(os.path.join(addon, 'resources', 'images', 'fanart.jpg'), os.path.join(path, 'fanart.jpg'))

        if os.path.exists(os.path.join(addon, 'resources', 'images', 'screenshot01.png')):
            _log("copying screenshots...")
            for i in range(1, 6):
                try:
                    sspath = os.path.join(addon, 'resources', 'images', f'screenshot0{i}.png')
                    copyfile(sspath, os.path.join(path, f'screenshot0{i}.png'))
                    _log(f"copied {sspath}...")
                except Exception:
                    break

        with ZipFile(os.path.join(ZIPPATH, addon, f'{addon}-{version}.zip'), 'w') as addonzip:
            for root, dirs, files in os.walk(addon):
                _log(f"Root: {root}")
                _log(f"Dirs: {len(dirs)}")
                _log(f"Files: {len(files)}")
                for file_path in files:
                    if file_path.endswith('.zip'):
                        continue
                    _log(f"adding {os.path.join(root, file_path)}")
                    addonzip.write(os.path.join(root, file_path))
        os.chdir(home)

    def _zipit(self, fpath):
        fpath = fpath or "."
        _log(f"fpath in zipgen: {fpath}")
        dirs = os.listdir(fpath)
        _log(f"{len(dirs)} dirs found in zipgen")
        for addon_dir in dirs:
            directory = os.path.join(fpath, addon_dir)
            if not os.path.isdir(directory):
                continue
            if addon_dir.startswith('.'):
                continue
            if addon_dir.startswith("download"):
                continue
            _log(f"processing... {addon_dir}")
            self.create_zip_file(fpath, addon_dir)


if __name__ == "__main__":
    Generator()
