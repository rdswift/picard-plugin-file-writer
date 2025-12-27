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
from picard.plugin3.api import PluginApi
from picard.util import (
    is_absolute_path,
    normpath,
)
from picard.util.filenaming import make_save_path


RE_REPLACE_UNDERSCORES = re.compile(r'[\s_]+')


class ApiHelper:
    api: PluginApi = None

    @classmethod
    def initialize(cls, api: PluginApi):
        cls.api = api


def func_writeline(parser, file_to_write, text_to_write, reset_file=None):
    if file_to_write.strip():
        settings = ApiHelper.api.global_config.setting
        write_mode = 'w' if reset_file else 'a'
        if settings["replace_spaces_with_underscores"]:
            file_to_write = RE_REPLACE_UNDERSCORES.sub('_', file_to_write.strip())
        if not is_absolute_path(file_to_write):
            if settings['move_files'] and settings['move_files_to']:
                file_to_write = os.path.join(settings['move_files_to'], file_to_write)
        file_to_write = make_save_path(normpath(file_to_write), IS_WIN, IS_MACOS)
        try:
            os.makedirs(os.path.dirname(file_to_write), exist_ok=True)
            with open(file_to_write, write_mode, encoding='utf8') as f:
                f.write(text_to_write + '\n')
        except OSError as ex:
            ApiHelper.api.logger.error(f"Error writing to file: {file_to_write} (Exception: {ex})")
    else:
        ApiHelper.api.logger.error("Missing file path to write.")
    return ""


def enable(api: PluginApi):
    """Called when plugin is enabled."""
    ApiHelper().initialize(api)

    api.register_script_function(
        func_writeline,
        name="writeline",
        documentation=api.tr(
            'help.writeline',
            (
                "`$writeline(file,text[,reset])`\n\n"
                "Writes the text to the specified file. "
                "The text will be appended to the file unless `reset` is set, in which case the file will be overwritten. "
                "If the destination `file` path is not specified as an absolute path to the destination file (beginning "
                "with a Windows drive letter and colon or path separator), then the path will be considered relative to the "
                "***Destination directory*** specified in Picard's **File Naming Options** settings. If the target path does "
                "not exist, it will be created automatically."
            )
        )
    )
