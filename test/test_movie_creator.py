import unittest
import sys
sys.path.insert(1, 'absolute/path/to/movie-ads-creator')

from models.opencv_model.ad_insertion import AdInsertion
import numpy as np
import cv2 as cv
from pathlib import Path


class TestMovieCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = '../movie-ads-creator/src/conf/default_configurations.yaml'
        cls.video_path = 'test_data/test_video.mp4'
        cls.logo_path = 'test_data/test_logo.png'

        cls.files_path = str(Path.cwd()) + '/files'
        Path(cls.files_path).mkdir(parents=True, exist_ok=True)

        cls.output_path = str(Path.cwd()) + '/output'
        Path(cls.output_path).mkdir(parents=True, exist_ok=True)

        cls.base_capture = cv.VideoCapture(cls.video_path)
        cls.video_info = {'fps': cls.base_capture.get(cv.CAP_PROP_FPS),
                          'video_name': 'test_video',
                          'frame_width': int(cls.base_capture.get(3)),
                          'frame_height': int(cls.base_capture.get(4)),
                          'frame_square': int(cls.base_capture.get(3)) * int(cls.base_capture.get(4)),
                          'frames_count': int(cls.base_capture.get(cv.CAP_PROP_FRAME_COUNT))}
        cls.stable_contours = []
        cls.base_capture.release()

    def test_preprocessing(self):
        capture = cv.VideoCapture(self.video_path)
        data = []
        ad_insertion = []

        for i in range(self.video_info['frames_count']):
            ret, frame = capture.read()
            if ret:
                self.assertIsNotNone(frame)
                ad_insertion = AdInsertion(frame, self.logo_path, i, data, self.video_info)
                ad_insertion.build_model(self.config)
                ad_insertion.data_preprocessed()
            else:
                break

        self.assertGreater(self.video_info['frame_square'], 0)
        self.assertGreater(len(ad_insertion.contours), 0)

        capture.release()

    def test_detection(self):
        capture = cv.VideoCapture(self.video_path)
        data = []
        for i in range(self.video_info['frames_count']):
            ret, frame = capture.read()
            if ret:
                ad_insertion = AdInsertion(frame, self.logo_path, i, data, self.video_info)
                ad_insertion.build_model(self.config)
                ad_insertion.data_preprocessed()
            else:
                break
        data = np.array(data)
        np.save('files/data.npy', data)
        capture.release()

        ad_insertion = AdInsertion(None, None, None, None, self.video_info)
        ad_insertion.build_model(self.config)
        ad_insertion.detect_surfaces()
        stable_contours = ad_insertion.stable_contours
        self.assertGreater(len(stable_contours), 0)

    def test_insertion(self):
        capture = cv.VideoCapture(self.video_path)
        data = []
        for i in range(self.video_info['frames_count']):
            ret, frame = capture.read()
            if ret:
                ad_insertion = AdInsertion(frame, self.logo_path, i, data, self.video_info)
                ad_insertion.build_model(self.config)
                ad_insertion.data_preprocessed()
            else:
                break
        data = np.array(data)
        np.save('files/data.npy', data)
        capture.release()

        ad_insertion = AdInsertion(None, None, None, None, self.video_info)
        ad_insertion.build_model(self.config)
        ad_insertion.detect_surfaces()
        stable_contours = ad_insertion.stable_contours

        if len(stable_contours) != 0:
            capture = cv.VideoCapture(self.video_path)
            for i in range(self.video_info['frames_count']):
                ret, frame = capture.read()
                if ret:
                    if i in stable_contours[:, 0]:
                        ad_insertion = AdInsertion(frame, self.logo_path, i, None, self.video_info)
                        ad_insertion.build_model(self.config)
                        ad_insertion.insert_ad(stable_contours)
                        self.assertIsNotNone(ad_insertion.single_cnt)
                        self.assertEqual(ad_insertion.frame.shape, ad_insertion.logo.shape)
                else:
                    break
            capture.release()


if __name__ == '__main__':
    unittest.main()
