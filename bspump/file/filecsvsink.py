import csv
import logging
from ..abc.sink import Sink
import asyncio
from datetime import datetime
from asab.timer import Timer
#

L = logging.getLogger(__file__)

#

class FileCSVSink(Sink):

	ConfigDefaults = {
		'path': '',
		'dialect': 'excel',
		'delimiter': ',',
		'doublequote': True,
		'escapechar': "",
		'lineterminator': '\r\n',
		'quotechar': '"',
		'quoting': csv.QUOTE_MINIMAL,  # 0 - 3 for [QUOTE_MINIMAL, QUOTE_ALL, QUOTE_NONNUMERIC, QUOTE_NONE]
		'skipinitialspace': False,
		'strict': False,
		'output_queue_max_size': 500,
	}

	def __init__(self, app, pipeline, id=None, config=None):
		super().__init__(app, pipeline, id=id, config=config)
		self.Dialect = csv.get_dialect(self.Config['dialect'])
		self._csv_writer = None
		self._output_queue_max_size = int(self.Config['output_queue_max_size'])
		assert (self._output_queue_max_size >= 1), "Output queue max size invalid"
		self._conn_future = None
		self._output_queue = asyncio.Queue()
#		app.PubSub.subscribe("Application.tick!", self.write_to_file)
		self.num = 0
		self.FlushPeriod = int(10)
		self.AnalyzeTimer = Timer(app, self.write_to_file, autorestart=True)
		self.AnalyzeTimer.start(self.FlushPeriod)

	def get_file_name(self, context, event):
		'''
		Override this method to gain control over output file name.
		'''
		return self.Config['path']


	def writer(self, f, fieldnames):
		kwargs = dict()

		kwargs['delimiter'] = self.Config.get('delimiter')
		kwargs['doublequote'] = bool(self.Config.get('doublequote'))

		escape_char = self.Config.get('escapechar')
		escape_char = None if escape_char == "" else escape_char
		kwargs['escapechar'] = escape_char

		kwargs['lineterminator'] = self.Config.get('lineterminator')
		kwargs['quotechar'] = self.Config.get('quotechar')
		kwargs['quoting'] = int(self.Config.get('quoting'))
		kwargs['skipinitialspace'] = bool(self.Config.get('skipinitialspace'))
		kwargs['strict'] = bool(self.Config.get('strict'))

		return csv.DictWriter(f,
			dialect=self.Dialect,
			fieldnames=fieldnames,
			**kwargs
		)

	async def write_to_file(self):
		while True:
			self.num +=1
			context, item = await self._output_queue.get()
			print(context)
			print(item)
			if self._output_queue.qsize() == 0:
				print("Queue empty")
				break
			if self._csv_writer is None:
				# Open CSV file if needed
				fieldnames = item.keys()
				print(type(item))
				print(context)
				fname = str(datetime.now().time()).replace(":", "_").replace(".", "_") + ".csv"
				fo = open(fname, 'w', newline='')
				self._csv_writer = self.writer(fo, fieldnames)
				self._csv_writer.writeheader()
				print("saving..")
			self._csv_writer.writerow(item)
			self._output_queue.task_done()
			print(f"druha{self._output_queue.qsize()}")
		self.rotate()

	def process(self, context, event: [dict, list]):
		# This is where we check if the queue is overflowing in which case we apply throttling.
		if self._output_queue.qsize() >= self._output_queue_max_size:
			self.Pipeline.throttle(self, True)
		# Here,  we take the event (in this case it should be either a dictionary or a list of dictionaries,
		# and insert it into the queue to be available to the _outflux method.
		self._output_queue.put_nowait([context, event])


	def rotate(self):
		'''
		Call this to close the currently open file.
		'''
		del self._csv_writer
		self._csv_writer = None
