
import abc


__all__ = ("Messageable",)


class Messageable(abc.ABC):

    @abc.abstractmethod
    def message(self, message): ...
