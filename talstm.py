import collections
import tensorflow as tf
import numpy as np

from tensorflow.contrib.rnn import LSTMStateTuple, RNNCell

class TimeAwareLSTMCell(RNNCell):
	"""Basic LSTM recurrent network cell.
	The implementation is based on: http://arxiv.org/abs/1409.2329.
	We add forget_bias (default: 1) to the biases of the forget gate in order to
	reduce the scale of forgetting in the beginning of the training.
	It does not allow cell clipping, a projection layer, and does not
	use peep-hole connections: it is the basic baseline.
	For advanced models, please use the full @{tf.nn.rnn_cell.LSTMCell}
	that follows.
	"""

	def __init__(self, num_units, forget_bias=1.0,
							 state_is_tuple=True, activation=None, reuse=None):
		"""Initialize the basic LSTM cell.
		Args:
			num_units: int, The number of units in the LSTM cell.
			forget_bias: float, The bias added to forget gates (see above).
				Must set to `0.0` manually when restoring from CudnnLSTM-trained
				checkpoints.
			state_is_tuple: If True, accepted and returned states are 2-tuples of
				the `c_state` and `m_state`.  If False, they are concatenated
				along the column axis.  The latter behavior will soon be deprecated.
			activation: Activation function of the inner states.  Default: `tanh`.
			reuse: (optional) Python boolean describing whether to reuse variables
				in an existing scope.  If not `True`, and the existing scope already has
				the given variables, an error is raised.
			When restoring from CudnnLSTM-trained checkpoints, must use
			CudnnCompatibleLSTMCell instead.
		"""
		super(TimeAwareLSTMCell, self).__init__(_reuse=reuse)
		if not state_is_tuple:
			logging.warn("%s: Using a concatenated state is slower and will soon be "
									 "deprecated.  Use state_is_tuple=True.", self)
		self._num_units = num_units
		self._forget_bias = forget_bias
		self._state_is_tuple = state_is_tuple
		self._activation = activation or tf.tanh

	@property
	def state_size(self):
		return (LSTMStateTuple(self._num_units, self._num_units)
						if self._state_is_tuple else 2 * self._num_units)

	@property
	def output_size(self):
		return self._num_units

	def call(self, inputs, state):
		"""Long short-term memory cell (LSTM).
		Args:
			inputs: `2-D` tensor with shape `[batch_size x input_size]`.
			state: An `LSTMStateTuple` of state tensors, each shaped
				`[batch_size x self.state_size]`, if `state_is_tuple` has been set to
				`True`.  Otherwise, a `Tensor` shaped
				`[batch_size x 2 * self.state_size]`.
		Returns:
			A pair containing the new hidden state, and the new state (either a
				`LSTMStateTuple` or a concatenated state, depending on
				`state_is_tuple`).
		"""
		sigmoid = tf.sigmoid
		# Parameters of gates are concatenated into one multiply for efficiency.
		if self._state_is_tuple:
			c, h = state
		else:
			c, h = tf.split(value=state, num_or_size_splits=2, axis=1)


		# the last element in every input is dt
		inputs, dt = tf.split(inputs, [int(inputs.shape[1]) - 1, 1], 1)


		#g = 1 / dt
		g = 1 / tf.log(np.e + dt)

		# adjust c
		c_short = tf.layers.dense(c, self._num_units, activation=self._activation)
		discounted_short = c_short * g

		c_long = c - c_short
		c = c_long + discounted_short

		concat = tf.concat([inputs, h], 1)
		concat = tf.layers.dense(concat, 4 * self._num_units)

		# i = input_gate, j = new_input, f = forget_gate, o = output_gate
		i, j, f, o = tf.split(value=concat, num_or_size_splits=4, axis=1)

		new_c = (
				c * sigmoid(f + self._forget_bias) + sigmoid(i) * self._activation(j))
		new_h = self._activation(new_c) * sigmoid(o)

		if self._state_is_tuple:
			new_state = LSTMStateTuple(new_c, new_h)
		else:
			new_state = tf.concat([new_c, new_h], 1)
		return new_h, new_state