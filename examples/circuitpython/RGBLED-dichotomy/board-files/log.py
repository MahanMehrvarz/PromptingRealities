# Colors
#   0: Black
#   1: Red
#   2: Green
#   3: Yellow
#   4: Blue
#   5: Magenta
#   6: Cyan
#   7: White


class Log():
	def __init__(self, name, color):
		self.name = "[{}]".format(name)
		self.color = "\033[1;3{}m".format(color)
	
	def __call__(self, *args):
		print(self.color, self.name, "\033[0m ", end="", sep="")
		print(*args)

	def error(self, *args):
		print(self.color, self.name, " \033[1m\033[31mERROR\033[0m ", end="", sep="")
		print(*args)
