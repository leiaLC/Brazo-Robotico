# generated from rosidl_generator_py/resource/_idl.py.em
# with input from robot_interfaces:msg/DetectedObject.idl
# generated code does not contain a copyright notice

# This is being done at the module level and not on the instance level to avoid looking
# for the same variable multiple times on each instance. This variable is not supposed to
# change during runtime so it makes sense to only look for it once.
from os import getenv

ros_python_check_fields = getenv('ROS_PYTHON_CHECK_FIELDS', default='')


# Import statements for member types

# Member 'mask'
import array  # noqa: E402, I100

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_DetectedObject(type):
    """Metaclass of message 'DetectedObject'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('robot_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'robot_interfaces.msg.DetectedObject')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__detected_object
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__detected_object
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__detected_object
            cls._TYPE_SUPPORT = module.type_support_msg__msg__detected_object
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__detected_object

            from std_msgs.msg import Header
            if Header.__class__._TYPE_SUPPORT is None:
                Header.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class DetectedObject(metaclass=Metaclass_DetectedObject):
    """Message class 'DetectedObject'."""

    __slots__ = [
        '_header',
        '_class_id',
        '_label',
        '_confidence',
        '_bbox_x1',
        '_bbox_y1',
        '_bbox_x2',
        '_bbox_y2',
        '_center_u',
        '_center_v',
        '_mask',
        '_mask_width',
        '_mask_height',
        '_x',
        '_y',
        '_z',
        '_depth_valid',
        '_check_fields',
    ]

    _fields_and_field_types = {
        'header': 'std_msgs/Header',
        'class_id': 'int32',
        'label': 'string',
        'confidence': 'float',
        'bbox_x1': 'float',
        'bbox_y1': 'float',
        'bbox_x2': 'float',
        'bbox_y2': 'float',
        'center_u': 'float',
        'center_v': 'float',
        'mask': 'sequence<float>',
        'mask_width': 'int32',
        'mask_height': 'int32',
        'x': 'float',
        'y': 'float',
        'z': 'float',
        'depth_valid': 'boolean',
    }

    # This attribute is used to store an rosidl_parser.definition variable
    # related to the data type of each of the components the message.
    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['std_msgs', 'msg'], 'Header'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.UnboundedSequence(rosidl_parser.definition.BasicType('float')),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        if 'check_fields' in kwargs:
            self._check_fields = kwargs['check_fields']
        else:
            self._check_fields = ros_python_check_fields == '1'
        if self._check_fields:
            assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
                'Invalid arguments passed to constructor: %s' % \
                ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from std_msgs.msg import Header
        self.header = kwargs.get('header', Header())
        self.class_id = kwargs.get('class_id', int())
        self.label = kwargs.get('label', str())
        self.confidence = kwargs.get('confidence', float())
        self.bbox_x1 = kwargs.get('bbox_x1', float())
        self.bbox_y1 = kwargs.get('bbox_y1', float())
        self.bbox_x2 = kwargs.get('bbox_x2', float())
        self.bbox_y2 = kwargs.get('bbox_y2', float())
        self.center_u = kwargs.get('center_u', float())
        self.center_v = kwargs.get('center_v', float())
        self.mask = array.array('f', kwargs.get('mask', []))
        self.mask_width = kwargs.get('mask_width', int())
        self.mask_height = kwargs.get('mask_height', int())
        self.x = kwargs.get('x', float())
        self.y = kwargs.get('y', float())
        self.z = kwargs.get('z', float())
        self.depth_valid = kwargs.get('depth_valid', bool())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.get_fields_and_field_types().keys(), self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    if self._check_fields:
                        assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.header != other.header:
            return False
        if self.class_id != other.class_id:
            return False
        if self.label != other.label:
            return False
        if self.confidence != other.confidence:
            return False
        if self.bbox_x1 != other.bbox_x1:
            return False
        if self.bbox_y1 != other.bbox_y1:
            return False
        if self.bbox_x2 != other.bbox_x2:
            return False
        if self.bbox_y2 != other.bbox_y2:
            return False
        if self.center_u != other.center_u:
            return False
        if self.center_v != other.center_v:
            return False
        if self.mask != other.mask:
            return False
        if self.mask_width != other.mask_width:
            return False
        if self.mask_height != other.mask_height:
            return False
        if self.x != other.x:
            return False
        if self.y != other.y:
            return False
        if self.z != other.z:
            return False
        if self.depth_valid != other.depth_valid:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def header(self):
        """Message field 'header'."""
        return self._header

    @header.setter
    def header(self, value):
        if self._check_fields:
            from std_msgs.msg import Header
            assert \
                isinstance(value, Header), \
                "The 'header' field must be a sub message of type 'Header'"
        self._header = value

    @builtins.property
    def class_id(self):
        """Message field 'class_id'."""
        return self._class_id

    @class_id.setter
    def class_id(self, value):
        if self._check_fields:
            assert \
                isinstance(value, int), \
                "The 'class_id' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'class_id' field must be an integer in [-2147483648, 2147483647]"
        self._class_id = value

    @builtins.property
    def label(self):
        """Message field 'label'."""
        return self._label

    @label.setter
    def label(self, value):
        if self._check_fields:
            assert \
                isinstance(value, str), \
                "The 'label' field must be of type 'str'"
        self._label = value

    @builtins.property
    def confidence(self):
        """Message field 'confidence'."""
        return self._confidence

    @confidence.setter
    def confidence(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'confidence' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'confidence' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._confidence = value

    @builtins.property
    def bbox_x1(self):
        """Message field 'bbox_x1'."""
        return self._bbox_x1

    @bbox_x1.setter
    def bbox_x1(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'bbox_x1' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'bbox_x1' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._bbox_x1 = value

    @builtins.property
    def bbox_y1(self):
        """Message field 'bbox_y1'."""
        return self._bbox_y1

    @bbox_y1.setter
    def bbox_y1(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'bbox_y1' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'bbox_y1' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._bbox_y1 = value

    @builtins.property
    def bbox_x2(self):
        """Message field 'bbox_x2'."""
        return self._bbox_x2

    @bbox_x2.setter
    def bbox_x2(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'bbox_x2' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'bbox_x2' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._bbox_x2 = value

    @builtins.property
    def bbox_y2(self):
        """Message field 'bbox_y2'."""
        return self._bbox_y2

    @bbox_y2.setter
    def bbox_y2(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'bbox_y2' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'bbox_y2' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._bbox_y2 = value

    @builtins.property
    def center_u(self):
        """Message field 'center_u'."""
        return self._center_u

    @center_u.setter
    def center_u(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'center_u' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'center_u' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._center_u = value

    @builtins.property
    def center_v(self):
        """Message field 'center_v'."""
        return self._center_v

    @center_v.setter
    def center_v(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'center_v' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'center_v' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._center_v = value

    @builtins.property
    def mask(self):
        """Message field 'mask'."""
        return self._mask

    @mask.setter
    def mask(self, value):
        if self._check_fields:
            if isinstance(value, array.array):
                assert value.typecode == 'f', \
                    "The 'mask' array.array() must have the type code of 'f'"
                self._mask = value
                return
            from collections.abc import Sequence
            from collections.abc import Set
            from collections import UserList
            from collections import UserString
            assert \
                ((isinstance(value, Sequence) or
                  isinstance(value, Set) or
                  isinstance(value, UserList)) and
                 not isinstance(value, str) and
                 not isinstance(value, UserString) and
                 all(isinstance(v, float) for v in value) and
                 all(not (val < -3.402823466e+38 or val > 3.402823466e+38) or math.isinf(val) for val in value)), \
                "The 'mask' field must be a set or sequence and each value of type 'float' and each float in [-340282346600000016151267322115014000640.000000, 340282346600000016151267322115014000640.000000]"
        self._mask = array.array('f', value)

    @builtins.property
    def mask_width(self):
        """Message field 'mask_width'."""
        return self._mask_width

    @mask_width.setter
    def mask_width(self, value):
        if self._check_fields:
            assert \
                isinstance(value, int), \
                "The 'mask_width' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'mask_width' field must be an integer in [-2147483648, 2147483647]"
        self._mask_width = value

    @builtins.property
    def mask_height(self):
        """Message field 'mask_height'."""
        return self._mask_height

    @mask_height.setter
    def mask_height(self, value):
        if self._check_fields:
            assert \
                isinstance(value, int), \
                "The 'mask_height' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'mask_height' field must be an integer in [-2147483648, 2147483647]"
        self._mask_height = value

    @builtins.property
    def x(self):
        """Message field 'x'."""
        return self._x

    @x.setter
    def x(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'x' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'x' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._x = value

    @builtins.property
    def y(self):
        """Message field 'y'."""
        return self._y

    @y.setter
    def y(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'y' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'y' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._y = value

    @builtins.property
    def z(self):
        """Message field 'z'."""
        return self._z

    @z.setter
    def z(self, value):
        if self._check_fields:
            assert \
                isinstance(value, float), \
                "The 'z' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'z' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._z = value

    @builtins.property
    def depth_valid(self):
        """Message field 'depth_valid'."""
        return self._depth_valid

    @depth_valid.setter
    def depth_valid(self, value):
        if self._check_fields:
            assert \
                isinstance(value, bool), \
                "The 'depth_valid' field must be of type 'bool'"
        self._depth_valid = value
