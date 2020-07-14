import cv2 as cv
import numpy as np
import math
from models.AbstractAdInsertion import AbstractAdInsertion
from scipy.spatial import distance
from scipy.signal import savgol_filter
import yaml


class AdInsertion(AbstractAdInsertion):
    """
    The model provides advertisement insertion with OpenCV package
    """
    def __init__(self, frame, logo, frame_idx, data, video_info):
        self.frame = frame
        self.logo = logo
        self.fps = video_info['fps']
        self.contours = []
        self.single_cnt = []
        self.stable_contours = []
        self.data = data
        self.frame_idx = frame_idx
        self.video_name = video_info['video_name']
        self.logo_ratio = video_info['logo_ratio']
        self.frames_count = video_info['frames_count']
        self.instance_insertions = []
        self.config = {}

    def __find_contours(self, kernel, min_area, max_area, corners_count, perimeter_threshold):
        """
        Contours detection in the frame
        :param kernel: parameter for frame bluring
        :param min_area: minimal area threshold
        :param max_area: maximum area threshold
        :param corners_count: contour corners amount
        :param perimeter_threshold: contour approximation threshold
        :return:
        """
        gray = cv.cvtColor(self.frame, cv.COLOR_BGR2GRAY)
        blur_gray = cv.GaussianBlur(gray, (kernel, kernel), 0)

        _, th = cv.threshold(blur_gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        _, contours, __ = cv.findContours(th, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        drop_list = [i for i in range(len(contours))
                     if cv.contourArea(contours[i]) < min_area
                     or cv.contourArea(contours[i]) > max_area]
        contours = [i for j, i in enumerate(contours) if j not in drop_list]

        for cnt in contours:
            epsilon = perimeter_threshold * cv.arcLength(cnt, True)
            approx = cv.approxPolyDP(cnt, epsilon, True)
            corners = len(approx)
            convexity = cv.isContourConvex(approx)

            if convexity and corners == corners_count:
                self.contours.append(approx.tolist())

    def __create_data_structures(self):
        """
        Writing contours to array
        :return:
        """

        if self.contours != 0:
            for i, v in enumerate(self.contours):
                self.data.append([self.frame_idx,
                                  v[0][0][0], v[0][0][1], v[1][0][0], v[1][0][1],
                                  v[2][0][0], v[2][0][1], v[3][0][0], v[3][0][1]])

    def __clean_data(self, field_threshold, contours_threshold, dst_threshold):
        """
        Stable fields and contours detection
        :param field_threshold: minimum field duration threshold
        :param contours_threshold: minimum contours duration threshold
        :param dst_threshold: distance between contours centers
        :return:
        """
        data = np.load('files/data.npy')
        unique_idx = np.unique(data[:, 0])
        expected = [i if i in unique_idx else 'X' for i in range(self.frames_count)]
        x_ids = [i for i, j in enumerate(expected) if j == 'X']
        intervals = [[x_ids[i] + 1, x_ids[i + 1] - 1] for i in range(len(x_ids) - 1)
                     if (x_ids[i + 1] - x_ids[i]) > field_threshold]

        if x_ids[0] > field_threshold:
            intervals.insert(0, [0, x_ids[0]])

        if self.frames_count - x_ids[-1] > field_threshold:
            intervals.append([x_ids[-1] + 1, self.frames_count])

        for interval in intervals:
            condition = np.logical_and(data[:, 0] >= interval[0], data[:, 0] <= interval[1])
            stable = data[condition]

            prev_cnt = stable[0, :]
            prev_contour = np.array([[prev_cnt[1], prev_cnt[2]], [prev_cnt[3], prev_cnt[4]],
                                     [prev_cnt[5], prev_cnt[6]], [prev_cnt[7], prev_cnt[8]]])
            prev_m = cv.moments(prev_contour)
            prev_cx = int(prev_m['m10'] / prev_m['m00'])
            prev_cy = int(prev_m['m01'] / prev_m['m00'])
            stable_contour = []
            for i, row in enumerate(stable):

                if row[0] - prev_cnt[0] == 0:
                    continue

                elif row[0] - prev_cnt[0] == 1:
                    contour = np.array([[row[1], row[2]], [row[3], row[4]],
                                        [row[5], row[6]], [row[7], row[8]]])

                    m = cv.moments(contour)
                    base_cx = int(m['m10'] / m['m00'])
                    base_cy = int(m['m01'] / m['m00'])

                    dist = distance.euclidean([base_cx, base_cy], [prev_cx, prev_cy])
                    if dist < dst_threshold:
                        stable_contour.append(row)
                        prev_cnt = row
                        prev_cx = base_cx
                        prev_cy = base_cy

            if len(stable_contour) >= int(self.fps) * contours_threshold:
                self.stable_contours.append(np.array(stable_contour))

    def __define_contour_orientation(self):
        """
        Find contour corners orientation
        :return:
        """
        for field in self.stable_contours:
            for i in range(len(field)):
                contour = np.reshape(field[i][1:], (4, 2))
                contour = contour[contour[:, 0].argsort()]

                left_side = contour[:2]
                right_side = contour[2:]

                left_idx_max = np.ravel(np.argmax(left_side, axis=0))[1]
                left_idx_min = np.ravel(np.argmin(left_side, axis=0))[1]
                right_idx_max = np.ravel(np.argmax(right_side, axis=0))[1]
                right_idx_min = np.ravel(np.argmin(right_side, axis=0))[1]

                top_left = left_side[left_idx_min]
                bot_left = left_side[left_idx_max]
                top_right = right_side[right_idx_min]
                bot_right = right_side[right_idx_max]

                field[i] = np.array([field[i][0], top_left[0], top_left[1],
                                    bot_left[0], bot_left[1], bot_right[0],
                                    bot_right[1], top_right[0], top_right[1]])

    def __find_insertion_time_period(self):
        """
        Calculate video file time periods with ad insertion
        :return:
        """

        if len(self.stable_contours) != 0:
            with open('output/report_{}.txt'.format(self.video_name), 'w') as report:
                report.write('Total amount of insertions: {} \n'.format(len(self.stable_contours)))
                for i, contour in enumerate(self.stable_contours):
                    report.write('Period {}: \n'.format(i + 1))
                    begin = int(contour[:, 0][0] / math.ceil(self.fps))
                    b_time = divmod(begin, 60)
                    end = math.ceil(contour[:, 0][-1] / math.ceil(self.fps))
                    e_time = divmod(end, 60)
                    report.write('BEGIN: {} minutes {} seconds, END: {} minutes {} seconds \n'.format(b_time[0],
                                                                                                      b_time[1],
                                                                                                      e_time[0],
                                                                                                      e_time[1]))

    def __smooth_coordinates(self, window, poly_order):
        """
        Smoothing corners coordinated with Savitzky-Golay filter
        :param window: the length of filter window
        :param poly_order: the order of the polynomial used to fit the samples
        :return: stable contours amount
        """
        for field in self.stable_contours:
            for i in range(1, 9):
                field[:, i] = savgol_filter(field[:, i], window, poly_order)

        for field in self.stable_contours:
            self.instance_insertions.append(field[0])
        self.instance_insertions = np.array(self.instance_insertions)

        self.stable_contours = np.array(self.stable_contours)
        np.save('files/all_instances.npy', self.stable_contours)

    def __transform_logo(self, contours):
        """
        Transform logo according to frame shape
        :param contours: contours coordinates for logo transformation
        :return:
        """
        self.logo = cv.imread(self.logo, cv.IMREAD_UNCHANGED)
        row = contours[contours[:, 0] == self.frame_idx]
        self.single_cnt = [[row[0][1], row[0][2]], [row[0][3], row[0][4]],
                           [row[0][5], row[0][6]], [row[0][7], row[0][8]]]
        frame_h, frame_w, _ = self.frame.shape
        h, w, _ = self.logo.shape

        pts1 = np.float32([(0, 0), (0, (h - 1)), ((w - 1), (h - 1)), ((w - 1), 0)])
        pts2 = np.float32([self.single_cnt[0], self.single_cnt[1], self.single_cnt[2], self.single_cnt[3]])

        matrix = cv.getPerspectiveTransform(pts1, pts2)
        self.logo = cv.warpPerspective(self.logo, matrix, (frame_w, frame_h), borderMode=0)

    def build_model(self, filename):
        """
        Setting the required parameters for model building

        :param filename: file that contains required parameters for model tuning
        :return:
        """
        with open(filename, 'r') as stream:
            self.config = yaml.safe_load(stream)

    def data_preprocessed(self):
        """
        Data preparation for detection method
        :return:
        """
        cfg = self.config
        self.__find_contours(cfg['kernel'], cfg['min_area_threshold'],
                             cfg['max_area_threshold'], cfg['corners_count'],
                             cfg['perimeter_threshold'])
        self.__create_data_structures()

    def detect_surfaces(self):
        """
        Surface detection in the frame
        :return: contours quantity
        """
        cfg = self.config
        self.__clean_data(cfg['field_threshold'], cfg['contour_threshold'],
                          cfg['dst_threshold'])
        self.__define_contour_orientation()
        self.__find_insertion_time_period()
        self.__smooth_coordinates(cfg['window'], cfg['poly_order'])

    def insert_ad(self, contours):
        """
        Insert ad into the frame
        :param contours: contour for logo insertion
        :return:
        """
        frame_h, frame_w, _ = self.frame.shape
        self.__transform_logo(contours)
        if self.logo.shape[2] == 4:
            png_mask = self.logo[:, :, 3]
            bgr_logo = self.logo[:, :, 0:3]

            logo_roi = cv.bitwise_and(bgr_logo, bgr_logo, mask=png_mask)

            mask_inv = cv.bitwise_not(png_mask)
            frame_roi = cv.bitwise_and(self.frame, self.frame, mask=mask_inv)
            self.frame = cv.add(frame_roi, logo_roi)
        else:
            self.single_cnt = np.array(self.single_cnt)
            mask = np.zeros((frame_h, frame_w))
            cv.drawContours(mask, [self.single_cnt], -1, 1, -1)

            points = np.argwhere(mask == 1)
            for i, j in points:
                self.frame[i, j] = self.logo[i, j]
