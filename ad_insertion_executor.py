from models.opencv_model.ad_insertion import AdInsertion
import cv2 as cv
import numpy as np
import os
from pathlib import Path


class InfoStorage(object):
    def __init__(self, capture, logo):
        self.capture = capture
        self.logo = logo
        self.video_info = {}

    def get_info(self):
        frame_width = int(self.capture.get(3))
        frame_height = int(self.capture.get(4))
        frames_count = int(self.capture.get(cv.CAP_PROP_FRAME_COUNT))
        fps = self.capture.get(cv.CAP_PROP_FPS)
        logo_h, logo_w, _ = self.logo.shape
        logo_ratio = logo_h / logo_w

        self.video_info = {'fps': fps,
                           'width': frame_width,
                           'height': frame_height,
                           'logo_ratio': logo_ratio,
                           'frames_count': frames_count}


class ProcessingExecutor(object):
    def __init__(self, video, logo, config):
        self.video = video
        self.logo = logo
        self.config = config
        self.input_info = {}

    def __find_contours(self, capture):
        """
            Model processing
            :param capture: video object
            :return:
            """
        print('Searching contours...')
        data = []
        for i in range(self.input_info['frames_count']):
            ret, frame = capture.read()
            if ret:

                if i == int(self.input_info['frames_count'] * 0.25):
                    print('25% of the movie is processed.')
                if i == int(self.input_info['frames_count'] * 0.5):
                    print('50% of the movie is processed.')
                if i == int(self.input_info['frames_count'] * 0.75):
                    print('75% of the movie is processed')

                ad_insertion = AdInsertion(frame, None, i, data, self.input_info)
                ad_insertion.build_model(self.config)
                ad_insertion.data_preprocessed()
            else:
                break
        data = np.array(data)
        np.save('files/data.npy', data)
        capture.release()
        print('Searching is completed.')

    def __handle_contours(self):
        """
            Model detection method
            :return: stable contours
            """
        print('Handling contours...')
        ad_insertion = AdInsertion(None, None, None, None, self.input_info)
        ad_insertion.build_model(self.config)
        ad_insertion.detect_surfaces()
        instance_insertions = ad_insertion.instance_insertions
        print('Detected {} stable contours.'.format(len(instance_insertions)))
        print('Handling is completed.')
        return instance_insertions

    def __get_instances(self, video, logo, instances):
        """
            Create instance insertions
            :param video: video path
            :param logo: logo path
            :param instances: array with fields instances
            :return: message that describe function output
            """
        if len(instances) != 0:
            capture = cv.VideoCapture(video)
            ids = instances[:, 0]
            for i, frame_index in enumerate(ids):
                capture.set(cv.CAP_PROP_POS_FRAMES, frame_index)
                _, frame = capture.read()
                ad_insertion = AdInsertion(frame, logo, frame_index, None, self.input_info)
                ad_insertion.build_model(self.config)
                ad_insertion.insert_ad(instances)
                cv.imwrite('output/instances/{}.png'.format(i), ad_insertion.frame)
            capture.release()
            message = 'Insert templates are ready. Please check the templates for further actions.'
            print(message)
        else:
            message = 'No places to insert ad were found. Please try different video file.'
            print(message)

        return message

    def process_video(self):
        """
            Execute AdInsertion model for logo insertion
            :return: message that describes function output
            """
        # Creating folders for further actions
        input_video_name = self.video.split('.')[0]
        files_path = str(Path.cwd()) + '/files'
        output_path = str(Path.cwd()) + '/output'
        instances_path = output_path + '/instances'
        Path(files_path).mkdir(parents=True, exist_ok=True)
        Path(output_path).mkdir(parents=True, exist_ok=True)
        Path(instances_path).mkdir(parents=True, exist_ok=True)

        capture = cv.VideoCapture(output_path + '/' + self.video)
        read_logo = cv.imread(output_path + '/' + self.logo)

        if int(capture.get(cv.CAP_PROP_FPS)) == 0 or read_logo is None:
            message = 'ERROR WHILE ENTERING LOGO OR VIDEO PATH.'
            print(message)
        else:

            # Get input video info
            info_storage = InfoStorage(capture, read_logo)
            info_storage.get_info()
            self.input_info = info_storage.video_info
            self.input_info['video_name'] = input_video_name

            # Finding contours
            self.__find_contours(capture)

            # Handling contours
            instances = self.__handle_contours()

            # Getting instances
            message = self.__get_instances(output_path + '/' + self.video,
                                           output_path + '/' + self.logo,
                                           instances)
        return message


class InsertionExecutor(object):
    def __init__(self, video, logo, config):
        self.video = video
        self.logo = logo
        self.config = config
        self.all_contours = []
        self.input_info = {}
        self.folder_paths = []

    def __handle_instances(self, instances_path):
        """
            Handle instances after user checking
            :param instances_path: instances path
            :return:
            """
        list_idx = []
        for filename in os.listdir(instances_path):
            if filename == '.DS_Store':
                continue
            insertion_idx = int(filename.split('.')[0])
            list_idx.append(insertion_idx)

        stable_contours = np.load('files/all_instances.npy', allow_pickle=True)
        for i, contour in enumerate(stable_contours):
            if i in list_idx:
                for frame_contour in contour:
                    self.all_contours.append(frame_contour)
        self.all_contours = np.array(self.all_contours)

    def __add_audio(self, output_path, filename):
        """
            Extract audio file from input video and add it to output video
            :param output_path: output path
            :param filename: filename
            :return:
            """
        video_path = output_path + '/' + self.video
        idx = np.random.randint(0, 10000)
        audio_name = 'audio_{}_{}.m4a'.format(filename, idx)
        os.system('ffmpeg -i {} -vn -acodec copy files/{}'.format(video_path, audio_name))
        output = 'output/output_{}_{}.avi'.format(filename, idx)
        os.system('ffmpeg -i files/result.avi -i files/{} -codec copy -shortest {}'.format(audio_name, output))

    def __clean_folders(self):
        """
            Clean folders after execution
            :return:
            """
        for path in self.folder_paths:
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))

    def insert_ads(self):
        """
            Model insertion method
            :return: message that describes insertion result
            """
        video_name = self.video.split('.')[0]
        output_path = str(Path.cwd()) + '/output'
        files_path = str(Path.cwd()) + '/files'
        instances_path = output_path + '/instances'

        if len(os.listdir(files_path)) != 0:

            self.__handle_instances(instances_path)

            if len(self.all_contours) != 0:
                print('Insertion is running...')
                capture = cv.VideoCapture(output_path + '/' + self.video)
                read_logo = cv.imread(output_path + '/' + self.logo)

                info_storage = InfoStorage(capture, read_logo)
                info_storage.get_info()
                self.input_info = info_storage.video_info
                self.input_info['video_name'] = video_name

                four_cc = cv.VideoWriter_fourcc(*'FMP4')
                out_name = 'files/result.avi'
                out = cv.VideoWriter(out_name, four_cc, self.input_info['fps'],
                                     (self.input_info['width'], self.input_info['height']), True)

                for i in range(self.input_info['frames_count']):
                    ret, frame = capture.read()
                    if ret:

                        if i == int(self.input_info['frames_count'] * 0.25):
                            print('25% of the insertion is completed.')
                        if i == int(self.input_info['frames_count'] * 0.5):
                            print('50% of the insertion is completed.')
                        if i == int(self.input_info['frames_count'] * 0.75):
                            print('75% of the insertion is completed.')
                        if i in self.all_contours[:, 0]:
                            ad_insertion = AdInsertion(frame, output_path + '/' + self.logo,
                                                       i, None, self.input_info)
                            ad_insertion.build_model(self.config)
                            ad_insertion.insert_ad(self.all_contours)
                            out.write(ad_insertion.frame)
                        else:
                            out.write(frame)
                    else:
                        break
                self.__add_audio(output_path, video_name)
                capture.release()
                out.release()
                print('Insertion completed.')
                message = 'Video file has been processed.'
                print(message)

                self.folder_paths = [files_path, instances_path]
                self.__clean_folders()

            else:
                message = 'There is nothing to insert. Please try different video file.'
                print(message)
        else:
            message = 'Please run Video Processing before Advertisement Insertion.'
            print(message)

        return message
