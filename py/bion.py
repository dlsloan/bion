from collections import Mapping, Iterable
import struct

dict_type = dict
list_type = list
bytes_type = bytes
int_type = int
str_type = str
float_type = float

TYPE_NULL = b'\0'
TYPE_FLOAT = b'f'
TYPE_INT8 = b'b'
TYPE_INT16 = b'h'
TYPE_INT32 = b'l'
TYPE_INT64 = b'q'
TYPE_STR = b'S'
TYPE_BYTES = b'B'
TYPE_DICT = b'D'
TYPE_LIST = b'L'
TYPE_REF = b'R'

class RefCmp:
	def __init__(self):
		self.dicts = []
		self.lists = []
		self.hashables = {}
		self.count = 0

	def checkRef(self, obj):
		if isinstance(obj, Mapping):
			for v in self.dicts:
				if v[0] is obj:
					return v[1]
			self.dicts += [(obj, self.count)]
			self.count += 1
		elif isinstance(obj, Iterable):
			for v in self.lists:
				if v[0] is obj:
					return v[1]
			self.lists += [(obj, self.count)]
			self.count += 1
		elif isinstance(obj, bytes):
			if obj in self.hashables:
				return self.hashables[obj]
			self.hashables[obj] = self.count
			self.count += 1
		elif isinstance(obj, str):
			if obj in self.hashables:
				return self.hashables[obj]
			self.hashables[obj] = self.count
			self.count += 1
		return -1

def _load(raw, refs):
	if raw[:1] == TYPE_NULL:
		return raw[1:], None
	elif raw[:1] == TYPE_FLOAT:
		return raw[9:], float_type(struct.unpack('d', raw[1:9])[0])
	elif raw[:1] == TYPE_INT8:
		return raw[2:], int_type(struct.unpack('b', raw[1:2])[0])
	elif raw[:1] == TYPE_INT16:
		return raw[3:], int_type(struct.unpack('h', raw[1:3])[0])
	elif raw[:1] == TYPE_INT32:
		return raw[5:], int_type(struct.unpack('i', raw[1:5])[0])
	elif raw[:1] == TYPE_INT64:
		return raw[9:], int_type(struct.unpack('q', raw[1:9])[0])
	elif raw[:1] == TYPE_STR:
		raw, length = _load(raw[1:], refs)
		value = str_type(raw[:length].decode())
		refs += [value]
		return raw[length:], value
	elif raw[:1] == TYPE_BYTES:
		raw, length = _load(raw[1:], refs)
		value = bytes_type(raw[:length])
		refs += [value]
		return raw[length:], value
	elif raw[:1] == TYPE_DICT:
		raw, length = _load(raw[1:], refs)
		value = dict_type()
		refs += [value]
		for i in range(length):
			raw, key = _load(raw, refs)
			raw, val = _load(raw, refs)
			value[key] = val
		return raw, value
	elif raw[:1] == TYPE_LIST:
		raw, length = _load(raw[1:], refs)
		val = list_type()
		refs += [val]
		for i in range(length):
			raw, value = _load(raw, refs)
			val += [value]
		return raw, val
	elif raw[:1] == TYPE_REF:
		raw, index = _load(raw[1:], refs)
		return raw, refs[index]
	else:
		raise ValueError(f"Unrecognized type: {raw[:1]}")

def load(raw):
	refs = []
	raw, value =  _load(raw, refs)
	return value

def _dump(obj, val, refs):
	index = refs.checkRef(obj)
	if obj is None:
		return val + TYPE_NULL
	elif index != -1:
		return _dump(index, val + TYPE_REF, refs)
	elif isinstance(obj, float):
		return val + TYPE_FLOAT + struct.pack('d', obj)
	elif isinstance(obj, int):
		if obj & 0xff:
			return val + TYPE_INT8 + struct.pack('b', obj)
		elif obj & 0xffff:
			return val + TYPE_INT16 + struct.pack('h', obj)
		elif obj & 0xffffffff:
			return val + TYPE_INT32 + struct.pack('i', obj)
		else:
			return val + TYPE_INT64 + struct.pack('q', obj)
	elif isinstance(obj, str):
		raw = obj.encode()
		return _dump(len(raw), val + TYPE_STR, refs) + raw
	elif isinstance(obj, bytes):
		return _dump(len(obj), val + TYPE_BYTES, refs) + obj
	elif isinstance(obj, Mapping):
		val = _dump(len(obj), val + TYPE_DICT, refs)
		for k in obj:
			if not isinstance(k, str):
				raise KeyError('keys must be strings')
			val = _dump(k, val, refs)
			val = _dump(obj[k], val, refs)
		return val
	elif isinstance(obj, Iterable):
		val = _dump(len(obj), val + TYPE_LIST, refs)
		for v in obj:
			val = _dump(v, val, refs)
		return val
	else:
		raise ValueError(f"Invalid type: {type(obj).__name__}")

def dump(obj):
	return _dump(obj, b'', RefCmp())

# MIT License
# 
# Copyright (c) 2020 dlsloan
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.