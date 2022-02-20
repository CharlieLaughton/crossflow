from crossflow import filehandling, tasks
import tempfile
import os.path as op
import os
import pytest

def test_subprocess_task_no_filehandles(tmpdir):
    sk = tasks.SubprocessTask('cat file.txt')
    sk.set_inputs(['file.txt'])
    sk.set_outputs([tasks.STDOUT])
    p = tmpdir.mkdir('sub').join("hello.txt")
    p.write("content")
    result = sk.run(p)
    assert result == 'content'

def test_subprocess_task_stdout(tmpdir):
    sk = tasks.SubprocessTask('cat file.txt')
    sk.set_inputs(['file.txt'])
    sk.set_outputs([tasks.STDOUT])
    p = tmpdir.mkdir('sub').join("hello.txt")
    p.write("content")
    fh = filehandling.FileHandler()
    l = fh.load(p)
    result = sk.run(l)
    assert result == 'content'

def test_subprocess_task_fileout(tmpdir):
    sk = tasks.SubprocessTask('cat file.txt > out.dat')
    sk.set_inputs(['file.txt'])
    sk.set_outputs(['out.dat'])
    p = tmpdir.mkdir('sub').join("hello.txt")
    p.write("content")
    fh = filehandling.FileHandler()
    l = fh.load(p)
    result = sk.run(l)
    assert isinstance(result, filehandling.FileHandle)

def test_subprocess_task_globinputs(tmpdir):
    sk = tasks.SubprocessTask('cat *.txt > out.dat')
    sk.set_inputs(['*.txt'])
    sk.set_outputs(['out.dat'])
    d = tmpdir.mkdir('sub')
    p = d.join("file1.txt")
    q = d.join("file2.txt")
    p.write("content\n")
    q.write("more content\n")
    fh = filehandling.FileHandler()
    l = [fh.load(x) for x in [p, q]]
    result = sk.run(l)
    r = d.join("output.dat")
    result.save(r)
    assert r.read() == 'content\nmore content\n'

def test_subprocess_task_globoutputs(tmpdir):
    sk = tasks.SubprocessTask('split -l 1 input.txt')
    sk.set_inputs(['input.txt'])
    sk.set_outputs(['x*'])
    d = tmpdir.mkdir('sub')
    p = d.join("lines.txt")
    p.write("line 1\nline 2\nline 3\n")
    fh = filehandling.FileHandler()
    l = fh.load(p)
    result = sk.run(l)
    assert len(result) == 3

def test_subprocess_task_fails():
    with pytest.raises(tasks.XflowError):
        sk = tasks.SubprocessTask('foo -bar')
        sk.set_outputs([tasks.STDOUT])
        result = sk.run()

def test_subprocess_task_catch_fail():
    sk = tasks.SubprocessTask('foo -bar')
    sk.set_outputs([tasks.DEBUGINFO])
    result = sk.run()
    assert isinstance(result, tasks.XflowError)

def test_function_task_basic():
    def mult(a, b):
        return a * b

    fk = tasks.FunctionTask(mult)
    fk.set_inputs(['a', 'b'])
    fk.set_outputs(['ab'])
    result = fk.run(3, 4)
    assert result == 12

def test_function_task_with_filehandles(tmpdir):
    d = tmpdir.mkdir('sub')
    p = d.join("lines.txt")
    p.write("line 1\nline 2\nline 3\n")
    fh = filehandling.FileHandler()
    l = fh.load(p)

    def linecount(a):
        with open(a) as f:
            lines = f.readlines()
        return len(lines)

    fk = tasks.FunctionTask(linecount)
    fk.set_inputs(['a'])
    fk.set_outputs(['nlines'])
    result = fk.run(l)
    assert result == 3

def test_function_task_no_filehandles(tmpdir):
    d = tmpdir.mkdir('sub')
    p = d.join("lines.txt")
    p.write("line 1\nline 2\nline 3\n")
    def linecount(a):
        with open(a) as f:
            lines = f.readlines()
        return len(lines)

    fk = tasks.FunctionTask(linecount)
    fk.set_inputs(['a'])
    fk.set_outputs(['nlines'])
    result = fk.run(p)
    assert result == 3