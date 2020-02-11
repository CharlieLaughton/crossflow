'''
Clients.py: thin wrapper over dask client
'''
import socket
import subprocess
import tempfile
from dask.distributed import Client as DaskClient
from dask.distributed import LocalCluster
from .kernels import FunctionKernel, SubprocessKernel

def dask_client(scheduler_file=None, local=False, port=8786):
    """
    returns an instance of a dask.distributed client
    """
    if local:
#        if __name__ == '__main__':
            workdir = tempfile.mkdtemp()
            cluster = LocalCluster(local_directory=workdir)
            client = DaskClient(cluster)
#        else:
#            raise IOError('Error: local cluster must be started within the __main__ block of the script not from {}'.format(__name__))

    elif scheduler_file:
        client = DaskClient(scheduler_file=scheduler_file)
    else:
        ip_address = socket.gethostbyname(socket.gethostname())
        dask_scheduler = '{}:{}'.format(ip_address, port)
        try:
            client = DaskClient(dask_scheduler, timeout=5)
        except IOError:
            print('Error: cannot connect to dask scheduler at {}'.format(dask_scheduler))
            raise
    return client

class Client(object):
    '''Thin wrapper around Dask client so functions that return multiple
       values (tuples) generate tuples of futures rather than single futures.
    '''
    def __init__(self, **kwargs):
        self.client = dask_client(**kwargs)

    def close(self):
        """
        The close() method of the underlying dask client
        """
        return self.client.close

    def upload(self, some_object):
        """
        Upload some data/object to the.workers

        args:
            fsome_object (any type): what to upload

        returns:
            dask.Future
        """
        return self.client.scatter(some_object, broadcast=True)

    def unpack(self, kernel, future):
        """
        Unpacks the single future returned by kernel when run through
        a dask submit() or map() method, returning a tuple of futures.

        The outputs attribute of kernel lists how many values kernel
        should properly return.

        args:
            kernel (Kernel): the kernel that generated the future
            future (Future): the future returned by kernel

        returns:
            future or tuple of futures.
        """
        if len(kernel.outputs) == 1:
            return future
        outputs = []
        for i in range(len(kernel.outputs)):
            outputs.append(self.client.submit(lambda tup, j: tup[j], future, i))
        return tuple(outputs)

    def submit(self, func, *args):
        """
        Wrapper round the dask submit() method, so that a tuple of
        futures, rather than just one future, is returned.

        args:
            func (function/kernel): the function to be run
            args (list): the function arguments
        returns:
            future or tuple of futures
        """
        if isinstance(func, SubprocessKernel):
            future = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, future)
        if isinstance(func, FunctionKernel):
            future = self.client.submit(func.run, *args, pure=False)
            return self.unpack(func, future)
        else:
            return self.client.submit(func, *args)

    def _lt2tl(self, l):
        '''converts a list of tuples to a tuple of lists'''
        result = []
        for i in range(len(l[0])):
            result.append([t[i] for t in l])
        return tuple(result)

    def map(self, func, *iterables):
        """
        Wrapper arounf the dask map() method so it returns lists of
        tuples of futures, rather than lists of futures.

        args:
            func (function): the function to be mapped
            iterables (iterables): the function arguments

        returns:
            list or tuple of lists: futures returned by the mapped function
        """
        its = []
        maxlen = 0
        for iterable in iterables:
            if isinstance(iterable, list):
                l = len(iterable)
                if l > maxlen:
                    maxlen = l
        for iterable in iterables:
            if isinstance(iterable, list):
                l = len(iterable)
                if l != maxlen:
                    raise ValueError('Error: not all iterables are same length')
                its.append(iterable)
            else:
                its.append([iterable] * maxlen)
        if isinstance(func, SubprocessKernel):
            futures = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, future) for future in futures]
        elif isinstance(func, FunctionKernel):
            futures = self.client.map(func.run, *its, pure=False)
            result = [self.unpack(func, future) for future in futures]
        else:
            result =  self.client.map(func, *its, pure=False)
        if isinstance(result[0], tuple):
            result = self._lt2tl(result)
        return result
