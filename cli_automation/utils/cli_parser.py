import subprocess


def cli_returncode(argument_string):
    p = subprocess.Popen(argument_string,shell=True,stdout=subprocess.PIPE)
    print str(p.communicate()[0])
    p.wait()
    rc = p.returncode
    return rc


def cli_output(argument_string):
    p = subprocess.Popen(argument_string,shell=True,stdout=subprocess.PIPE)
    out = str(p.communicate()[0])
    p.wait()
    return out








