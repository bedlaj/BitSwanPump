#!/usr/bin/env python3
import bspump
import bspump.socket
import bspump.common
import bspump.amqp

class SamplePipeline1(bspump.Pipeline):

	def __init__(self, app, pipeline_id, amqp_connection):
		super().__init__(app, pipeline_id)
		self.build(
			bspump.socket.TCPStreamSource(app, self),
			bspump.amqp.AMQPSink(app, self, amqp_connection)
		)

class SamplePipeline2(bspump.Pipeline):

	def __init__(self, app, pipeline_id, amqp_connection):
		super().__init__(app, pipeline_id)
		self.build(
			bspump.amqp.AMQPSource(app, self, amqp_connection),
			bspump.common.PPrintSink(app, self)
		)

if __name__ == '__main__':
	app = bspump.BSPumpApplication()

	amqp_connection = bspump.amqp.AMQPConnection(app)
	svc = app.get_service("bspump.PumpService")

	svc.add_pipelines(
		SamplePipeline1(app, 'SamplePipeline1', amqp_connection),
		SamplePipeline2(app, 'SamplePipeline2', amqp_connection),
	)

	app.run()
