import subprocess


def cli_returncode(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    print(str(p.communicate()[0]))
    p.wait()
    rc = p.returncode
    return rc


def cli_output(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    out = str(p.communicate()[0])
    p.wait()
    return out


def cli_error(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
    err = str(p.communicate()[1])
    p.wait()
    return err


def cli_response_parser(cli_resp, key_attr):
    arrResp = cli_resp.splitlines()
    for j in range(0, len(arrResp)):
        arrL = arrResp[j].split("|")
        for i in range(0, len(arrL)):
            arrL[i] = arrL[i].rstrip()
            arrL[i] = arrL[i].lstrip()
        if(len(arrL) > 1):
            if(arrL[1] == key_attr):
                return arrL[2]
