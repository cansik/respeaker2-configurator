from typing import TypeVar

from duit.annotation.Annotation import Annotation
from duit.model.DataField import DataField

M = TypeVar("M", bound=DataField)


class RespeakerParam(Annotation):
    """
    Annotation to bind a DataField to a ReSpeaker parameter.
    Stores parameter id, offset, type, min/max, readonly flag and info.
    """

    def __init__(
            self,
            pid: int,
            offset: int,
            typ: str,
            maximum: float,
            minimum: float,
            rw: str
    ):
        self.pid = pid
        self.offset = offset
        self.typ = typ  # 'int' or 'float'
        self.max = maximum
        self.min = minimum
        self.rw = rw  # 'rw' or 'ro'

    def _apply_annotation(self, model: M) -> M:
        if not isinstance(model, DataField):
            raise Exception(f"{type(self).__name__} can only annotate DataField")
        setattr(model, self._get_annotation_attribute_name(), self)
        return model

    @staticmethod
    def _get_annotation_attribute_name() -> str:
        return f"_respeaker_param_annotation"
