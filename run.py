# import eventlet
# eventlet.monkey_patch(thread=True)
import multiprocessing

from cognitests.helpers import main
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
