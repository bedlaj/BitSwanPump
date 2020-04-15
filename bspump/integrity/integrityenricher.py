import logging
import random
import string

import hashlib
import base64

import bspump

###

L = logging.getLogger(__name__)

###


class IntegrityEnricher(bspump.Processor):
	"""
	IntegrityEnricher is a enricher processor, which enriches JSON data
	by hashed events.

	Supported algorithms for cryptographic signing, default is SHA256
	'SHA256', 'dsaEncryption', 'MD4', 'sha256', 'sha3_512', 'DSA', 'sha3_256', 'sha3_384', 'SHA512', 'md5', 'SHA224',
	'MD5', 'sha', 'whirlpool', 'ripemd160', 'SHA384', 'ecdsa-with-SHA1', 'RIPEMD160', 'sha1', 'blake2s', 'shake_128',
	'blake2b', 'sha512', 'sha224', 'md4', 'SHA', 'dsaWithSHA', 'sha384', 'sha3_224', 'shake_256', 'DSA-SHA', 'SHA1'
	"""

	ConfigDefaults = {
		'algorithm': 'SHA256',
		'encoding': 'utf-8',
		'hash_target': 'context',  # f. e. used by ElasticSearchSink
		'hash_key': 'es_id',
		'prev_hash_target': 'event',
		'prev_hash_key': 'prev'
	}

	def __init__(self, app, pipeline, id=None, config=None):
		super().__init__(app, pipeline, id, config)
		self.Algorithm = self.Config['algorithm']
		self.Encoding = self.Config['encoding']
		self.HashTarget = self.Config['hash_target']
		self.HashKey = self.Config['hash_key']
		self.PrevHashTarget = self.Config['prev_hash_target']
		self.PrevHashKey = self.Config['prev_hash_key']
		self.PreviousHash = None

	def _encode_for_hash(self, value):
		return str(value).encode(self.Encoding)

	def process(self, context, event):

		# Check that the event is a dictionary
		assert isinstance(event, dict)

		# Check if hash / previous hash already present in event and if so, delete it from event
		event.pop(self.HashKey, None)
		event.pop(self.PrevHashKey, None)

		# Salt event - to ensure that events are not going to be the same after hash
		event["sgs"] = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=6))

		# Hash event using key, value, key, value ... sequence
		_hash = hashlib.new(self.Algorithm)
		for key in sorted(event.keys()):
			_hash.update(self._encode_for_hash(key))
			_hash.update(self._encode_for_hash(event[key]))
		_hash.update(self._encode_for_hash(event["sgs"]))
		hash_base64 = base64.b64encode(_hash.digest()).decode(self.Encoding)

		# Store the hash as base64 string
		if self.HashTarget == "context":
			context[self.HashKey] = hash_base64
		else:
			event[self.HashKey] = hash_base64

		# Set previous hash
		if self.PrevHashTarget == "context":
			context[self.PrevHashKey] = self.PreviousHash
		else:
			event[self.PrevHashKey] = self.PreviousHash

		# Actual hash will become previous hash in the next iteration
		self.PreviousHash = hash_base64

		return event
