import dataclasses
import pathlib
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from ua_naming.planning import Options, build_plan, execute_plan
from ua_naming.settings import load_config
from ua_naming.naming import build_new_filename


class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.config = load_config()
        self.options = Options(game='ANC', feature='Karaoke', language='CHS', date='261002', output_dir=str(self.root/'out'))

    def image(self, name='a.png', size=(1080,1080)):
        path = self.root/name
        Image.new('RGB',size,'red').save(path)
        return path

    def test_legacy_naming_matrix(self):
        cases = json.loads((pathlib.Path(__file__).parent/'legacy_naming_cases.json').read_text())
        self.assertEqual(len(cases), 96)
        for case in cases:
            with self.subTest(args=case['args']):
                with patch('ua_naming.naming.get_resolution',return_value='1080x1080'), patch('ua_naming.naming.get_video_duration_sec',return_value=30):
                    self.assertEqual(list(build_new_filename(*case['args'])),case['expected'])

    def test_complete_image_set_and_copy(self):
        paths = [self.image(f'{i}.png',tuple(map(int,r.split('x')))) for i,r in enumerate(self.config['image_resolutions'])]
        plan=build_plan(paths,self.options,self.config)
        self.assertFalse(plan.errors); self.assertFalse(plan.warnings)
        self.assertIn('정상: 6 / 6',plan.sets[0])
        self.assertEqual(len({f.destination.parent for f in plan.files}),1)
        self.assertFalse((self.root/'out').exists())  # Preview has no write effects.
        results,errors=execute_plan(plan)
        self.assertEqual(len(results),6); self.assertFalse(errors)
        for f in plan.files: self.assertEqual(f.source.read_bytes(),f.destination.read_bytes())

    def test_missing_unexpected_and_duplicate(self):
        paths=[self.image('a.png'),self.image('b.png'),self.image('extra.png',(10,20))]
        plan=build_plan(paths,self.options,self.config)
        self.assertTrue(any('누락' in w for w in plan.warnings))
        self.assertTrue(any('중복' in w for w in plan.warnings))
        self.assertTrue(any('예상 외' in w for w in plan.warnings))
        self.assertTrue(plan.errors)  # Same resolution also produces a name collision.
        renamed=dataclasses.replace(self.options,keep_name=True)
        plan=build_plan(paths,renamed,self.config)
        self.assertFalse(plan.errors); self.assertEqual(len(execute_plan(plan)[0]),3)

    def test_existing_and_late_collision(self):
        path=self.image(); plan=build_plan([path],self.options,self.config)
        dest=plan.files[0].destination; dest.parent.mkdir(); dest.write_bytes(b'preserve')
        self.assertTrue(build_plan([path],self.options,self.config).errors)
        with self.assertRaises(FileExistsError): execute_plan(plan)
        self.assertEqual(dest.read_bytes(),b'preserve')

    def test_source_changed_after_preview(self):
        path=self.image(); plan=build_plan([path],self.options,self.config)
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError): execute_plan(plan)
        self.assertFalse((self.root/'out').exists())

    def test_conversion_keep_name_replace_and_original_mode(self):
        path=self.image()
        options=dataclasses.replace(self.options,keep_name=True,output_format='JPG',find='a',replace='new',overwrite=True)
        plan=build_plan([path],options,self.config)
        self.assertEqual(plan.files[0].destination.name,'new.jpg')
        results,errors=execute_plan(plan)
        self.assertFalse(errors); self.assertFalse(path.exists())
        with Image.open(self.root/'new.jpg') as im:
            self.assertEqual(im.format,'JPEG'); self.assertEqual(im.size,(1080,1080))

    def test_failed_same_path_write_preserves_original(self):
        path=self.image(); before=path.read_bytes()
        options=dataclasses.replace(self.options,keep_name=True,overwrite=True,compression='강한 압축')
        plan=build_plan([path],options,self.config)
        with patch('ua_naming.planning.save_image_with_options',side_effect=OSError('disk error')):
            results,errors=execute_plan(plan)
        self.assertFalse(results); self.assertTrue(errors); self.assertEqual(path.read_bytes(),before)
        self.assertFalse(list(self.root.glob('.ua-*')))

    def test_compression_formats_preserve_dimensions(self):
        path=self.image()
        for fmt in ('JPG','PNG','WEBP'):
            for level in ('압축 안 함','약한 압축','강한 압축'):
                options=dataclasses.replace(self.options,output_format=fmt,compression=level,output_dir=str(self.root/f'{fmt}-{level}'))
                plan=build_plan([path],options,self.config)
                results,errors=execute_plan(plan)
                self.assertFalse(errors)
                with Image.open(plan.files[0].destination) as im:
                    self.assertEqual(im.size,(1080,1080))
                    self.assertEqual(im.format,'JPEG' if fmt=='JPG' else fmt)

    def test_case_insensitive_collision(self):
        path=self.image(); plan=build_plan([path],self.options,self.config)
        dest=plan.files[0].destination; dest.parent.mkdir()
        dest.with_name(dest.name.lower()).write_bytes(b'preserve')
        self.assertTrue(build_plan([path],self.options,self.config).errors)


    def test_invalid_date_name_and_corrupt_file(self):
        path=self.image()
        self.assertTrue(build_plan([path],dataclasses.replace(self.options,date='261332'),self.config).errors)
        self.assertTrue(build_plan([path],dataclasses.replace(self.options,find='Karaoke',replace='../escape'),self.config).errors)
        path.write_bytes(b'not image')
        self.assertTrue(build_plan([path],self.options,self.config).errors)

    def test_video_set_uses_pixels_even_with_aspect(self):
        paths=[]
        for i,res in enumerate(self.config['video_resolutions']):
            path=self.root/f'{i}.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=black:s={res}:d=0.1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(path)],check=True)
            paths.append(path)
        plan=build_plan(paths,self.options,self.config)
        self.assertFalse(plan.errors); self.assertFalse(plan.warnings)
        self.assertIn('정상: 3 / 3',plan.sets[0])
        self.assertEqual(len(execute_plan(plan)[0]),3)
        plan=build_plan(paths,dataclasses.replace(self.options,aspect='16x9',output_dir=str(self.root/'other')),self.config)
        self.assertIn('정상: 3 / 3',plan.sets[0]); self.assertTrue(plan.errors)

if __name__=='__main__': unittest.main()
