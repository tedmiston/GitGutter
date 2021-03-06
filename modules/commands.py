# -*- coding: utf-8 -*-
import os

import sublime_plugin

from . import compare
from . import events
from . import goto
from . import handler
from . import popup
from . import settings
from . import show_diff
from . import utils

# the reason why evaluation is skipped, which is printed to console
# if debug is set true and evaluation.
DISABLED_REASON = {
    1: 'disabled in settings',
    2: 'view is transient',
    3: 'view is scratch',
    4: 'view is readonly',
    5: 'view is a widget',
    6: 'view is a REPL',
    7: 'view encoding is Hexadecimal',
    8: 'file not in a working tree',
    9: 'git is not working'
}


class GitGutterCommand(sublime_plugin.TextCommand):

    # The map of sub commands and their implementation
    commands = {
        'jump_to_next_change': goto.next_change,
        'jump_to_prev_change': goto.prev_change,
        'compare_against_commit': compare.set_against_commit,
        'compare_against_file_commit': compare.set_against_file_commit,
        'compare_against_branch': compare.set_against_branch,
        'compare_against_tag': compare.set_against_tag,
        'compare_against_head': compare.set_against_head,
        'compare_against_origin': compare.set_against_origin,
        'show_compare': compare.show_compare,
        'show_diff_popup': popup.show_diff_popup
    }

    def __init__(self, *args, **kwargs):
        """Initialize GitGutterCommand object."""
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.settings = settings.ViewSettings(self.view)
        self.git_handler = handler.GitGutterHandler(self.view, self.settings)
        self.show_diff_handler = show_diff.GitGutterShowDiff(self.git_handler)
        # Last enabled state for change detection
        self._state = -1

    def is_enabled(self, **kwargs):
        """Determine if `git_gutter` command is _enabled to execute."""
        view = self.view
        state = 0

        # Keep idle, if disabled by user setting
        if not self.settings.get('enable'):
            state = 1
        # Don't handle unattached views
        elif not view.window():
            state = 2
        # Don't handle scratch views
        elif view.is_scratch():
            state = 3
        # Don't handle readonly views
        elif view.is_read_only():
            state = 4
        # Don't handle widgets
        elif view.settings().get('is_widget'):
            state = 5
        # Don't handle SublimeREPL views
        elif view.settings().get("repl"):
            state = 6
        # Don't handle binary files
        elif view.encoding() == 'Hexadecimal':
            state = 7
        else:
            queued_events = kwargs.get('events')
            # Validate work tree on certain events only
            validate = queued_events is None or queued_events & (
                events.LOAD | events.ACTIVATED | events.POST_SAVE)
            # Don't handle files outside a repository
            if not self.git_handler.work_tree(validate):
                state = 8
            # Keep quite if git is not working properly
            elif not self.git_handler.version(validate):
                state = 9

        # Handle changed state
        valid = state == 0
        if self._state != state:
            # File moved out of work-tree or repository gone
            if not valid:
                self.show_diff_handler.clear()
                self.git_handler.invalidate_view_file()
                if settings.get('debug'):
                    utils.log_message('disabled for "%s" because %s' % (
                        os.path.basename(self.view.file_name() or 'untitled'),
                        DISABLED_REASON[state]))
            # Save state for use in other modules
            view.settings().set('git_gutter_is_enabled', valid)
            # Save state for internal use
            self._state = state
        return valid

    def run(self, edit, **kwargs):
        """API entry point to run the `git_gutter` command."""
        action = kwargs.get('action')
        if action:
            command_func = self.commands.get(action)
            assert command_func, 'Unhandled sub command "%s"' % action
            return command_func(self, **kwargs)

        queued_events = kwargs.get('events', 0)
        if not queued_events & (events.LOAD | events.MODIFIED):
            # On 'load' the git file is not yet valid anyway.
            # On 'modified' is sent when user is typing.
            # The git repository will most likely not change then.
            self.git_handler.invalidate_git_file()
        self.show_diff_handler.run()


class GitGutterBaseCommand(sublime_plugin.TextCommand):
    def is_enabled(self, **kwargs):
        return self.view.settings().get('git_gutter_is_enabled', False)


class GitGutterShowCompareCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command('git_gutter', {'action': 'show_compare'})


class GitGutterCompareHeadCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command('git_gutter', {'action': 'compare_against_head'})


class GitGutterCompareOriginCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command(
            'git_gutter', {'action': 'compare_against_origin'})


class GitGutterCompareCommitCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command(
            'git_gutter', {'action': 'compare_against_commit'})


class GitGutterCompareFileCommitCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command(
            'git_gutter', {'action': 'compare_against_file_commit'})


class GitGutterCompareBranchCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command(
            'git_gutter', {'action': 'compare_against_branch'})


class GitGutterCompareTagCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command('git_gutter', {'action': 'compare_against_tag'})


class GitGutterNextChangeCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command('git_gutter', {'action': 'jump_to_next_change'})


class GitGutterPrevChangeCommand(GitGutterBaseCommand):
    def run(self, edit):
        self.view.run_command('git_gutter', {'action': 'jump_to_prev_change'})
