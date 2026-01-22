# -*- coding: utf-8 -*-
#
# Copyright (C) 2023, 2025 Bob Swift (rdswift)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.


import os
import re

from picard.const.sys import (
    IS_MACOS,
    IS_WIN,
)
from picard.plugin3.api import (
    PluginApi,
    OptionsPage,
    t_,
)
from picard.util import (
    is_absolute_path,
    normpath,
)
from picard.util.filenaming import make_save_path

from .ui_options_file_writer import Ui_FileWriterOptionsPage


RE_REPLACE_UNDERSCORES = re.compile(r'[\s_]+')

USER_GUIDE_URL = 'https://picard-plugins-user-guides.readthedocs.io/en/latest/file_writer/user_guide.html'


class ApiHelper:
    api: PluginApi = None

    @classmethod
    def initialize(cls, api: PluginApi):
        cls.api = api


class FileWriterOptionsPage(OptionsPage):

    TITLE = t_("ui.title", "File Writer")
    HELP_URL = USER_GUIDE_URL

    def __init__(self, parent=None):
        super(FileWriterOptionsPage, self).__init__(parent)
        self.ui = Ui_FileWriterOptionsPage()
        self.ui.setupUi(self)

    def set2text(self, files: set):
        files.discard('')   # Remove blank items
        return '\n'.join(sorted(files))

    def text2set(self, file_list: str):
        files = set(file_list.split('\n'))
        files.discard('')   # Remove blank items
        return files

    def load(self):
        self.ui.allowed_file_paths.setPlainText(self.set2text(self.api.plugin_config["files_allowed"]))
        self.ui.enable_file_writing.setChecked(self.api.plugin_config["writing_enabled"])

    def save(self):
        self.api.plugin_config["files_allowed"] = self.text2set(self.ui.allowed_file_paths.toPlainText())
        self.api.plugin_config["writing_enabled"] = self.ui.enable_file_writing.isChecked()


def func_writeline(parser, file_to_write, text_to_write, reset_file=None):
    api = ApiHelper.api
    settings = api.plugin_config
    global_settings = api.global_config.setting

    if not settings['writing_enabled']:
        api.logger.warning("File writing is disabled.")
        return ""

    file_to_write = file_to_write.strip()
    if not file_to_write:
        api.logger.error("Missing file path to write.")
        return ""

    # Files with relative paths allowed
    settings_allowed: set = settings["files_allowed"]

    # Fully expanded files for checking
    allowed_files = set()
    for file in settings_allowed:
        if not is_absolute_path(file):
            file = os.path.join(global_settings['move_files_to'], file)
        allowed_files.add(make_save_path(normpath(file), IS_WIN, IS_MACOS))

    if global_settings["replace_spaces_with_underscores"]:
        file_to_write = RE_REPLACE_UNDERSCORES.sub('_', file_to_write)
    ofile = file_to_write

    if not is_absolute_path(file_to_write):
        if global_settings['move_files'] and global_settings['move_files_to']:
            file_to_write = os.path.join(global_settings['move_files_to'], file_to_write)
        else:
            api.logger.warning("Move files not enabled. File not written: %s", file_to_write)
            return ""
    file_to_write = make_save_path(normpath(file_to_write), IS_WIN, IS_MACOS)

    if not os.path.exists(file_to_write):
        allowed_files.add(file_to_write)
        settings_allowed.add(ofile)
        settings["files_allowed"] = settings_allowed

    if file_to_write not in allowed_files:
        api.logger.warning("Existing file not in allowed list. File not written: %s", file_to_write)

    write_mode = 'w' if reset_file else 'a'
    try:
        os.makedirs(os.path.dirname(file_to_write), exist_ok=True)
        with open(file_to_write, write_mode, encoding='utf8') as f:
            f.write(text_to_write + '\n')
    except OSError as ex:
        api.logger.error(f"Error writing to file: {file_to_write} (Exception: {ex})")
    return ""


def enable(api: PluginApi):
    """Called when plugin is enabled."""
    ApiHelper().initialize(api)

    # Register configuration options
    api.plugin_config.register_option("files_allowed", set())
    api.plugin_config.register_option("writing_enabled", False)

    # Register options page
    api.register_options_page(FileWriterOptionsPage)

    # Register script function
    api.register_script_function(
        func_writeline,
        name="writeline",
        signature=api.tr('help.writeline.signature', '$writeline(file,text[,reset])'),
        documentation=api.tr(
            'help.writeline.documentation',
            (
                "Writes the text to the specified file. "
                "The text will be appended to the file unless `reset` is set, in which case the file will be overwritten. "
                "If the destination `file` path is not specified as an absolute path to the destination file (beginning "
                "with a Windows drive letter and colon or path separator), then the path will be considered relative to the "
                "***Destination directory*** specified in Picard's **File Naming** option settings. If the target path does "
                "not exist, it will be created automatically."
            )
        )
    )
