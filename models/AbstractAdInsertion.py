from abc import ABC, abstractmethod


class AbstractAdInsertion(ABC):
    @abstractmethod
    def build_model(self, filename):
        pass

    @abstractmethod
    def data_preprocessed(self):
        pass

    @abstractmethod
    def detect_surfaces(self):
        pass

    @abstractmethod
    def insert_ad(self, contours):
        pass
