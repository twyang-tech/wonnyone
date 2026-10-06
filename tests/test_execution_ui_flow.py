"""Check the single-confirmation execution gate without a display server."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy
import unittest
from ua_naming.planning import Plan, Options, PlannedFile, describe_plan
from ua_naming.media import MediaInfo
from ua_naming.dialogs import confirmation_summary


class ConfirmationFlowTests(unittest.TestCase):
    def test_preview_body_keeps_set_status_without_repeating_alerts(self):
        plan = Plan(Options())
        plan.sets = ['ANC / Karaoke / CHS\n이미지 세트 경고: 5 / 6 — 누락: 1200x628']
        plan.warnings = ['누락: 1200x628']
        plan.errors = ['소재명을 입력해주세요.']
        body = describe_plan(plan, include_warnings=False)
        self.assertIn('ANC / Karaoke / CHS', body)
        self.assertIn('이미지 세트 경고: 5 / 6', body)
        self.assertNotIn('누락: 1200x628', body)
        self.assertNotIn('소재명을 입력해주세요.', body)
        self.assertEqual(plan.warnings, ['누락: 1200x628'])
        self.assertEqual(plan.errors, ['소재명을 입력해주세요.'])

    def test_summary_has_counts_without_paths_or_warning_details(self):
        plan = Plan(Options())
        plan.files = [PlannedFile(Path('/tmp/private.png'), Path('/tmp/out/renamed.png'),
                                 MediaInfo('이미지', 'PNG', '1080x1080'), (0, 0))]
        plan.warnings = ['누락: 800x800']
        text = confirmation_summary(plan)
        for expected in ('총 1개', '이름 변경 예정 1개', '이미지 1개 / 영상 0개', '경고 1건'):
            self.assertIn(expected, text)
        self.assertNotIn('private.png', text)
        self.assertNotIn('800x800', text)

    def test_cancel_executes_nothing_and_confirm_executes_once(self):
        app = runpy.run_path(str(Path(__file__).resolve().parents[1]/'UA-Naming .py'))['App']
        method = app.run_process
        globals_ = method.__globals__
        for accepted in (False, True):
            fake = SimpleNamespace(selected_files=['sample'], current_options=Mock(return_value=Options()),
                                   refresh_actual_preview=Mock(), status_var=Mock())
            confirm = Mock(return_value=accepted)
            execute = Mock(return_value=(['saved.png'], []))
            with patch.dict(globals_, build_plan=Mock(return_value=Plan(Options())),
                            confirm_execution=confirm, execute_plan=execute, messagebox=Mock()):
                method(fake)
            confirm.assert_called_once()
            self.assertEqual(execute.call_count, int(accepted))

    def test_errors_block_confirmation_and_execution(self):
        app = runpy.run_path(str(Path(__file__).resolve().parents[1]/'UA-Naming .py'))['App']
        plan = Plan(Options(), errors=['collision'])
        fake = SimpleNamespace(selected_files=['sample'], current_options=Mock(return_value=Options()),
                               refresh_actual_preview=Mock(), status_var=Mock())
        confirm, execute = Mock(), Mock()
        with patch.dict(app.run_process.__globals__, build_plan=Mock(return_value=plan),
                        confirm_execution=confirm, execute_plan=execute):
            app.run_process(fake)
        confirm.assert_not_called()
        execute.assert_not_called()
