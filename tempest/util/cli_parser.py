import subprocess
import pexpect
import time

def cli_returncode(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    print(str(p.communicate()[0]))
    p.wait()
    rc = p.returncode
    return rc


def cli_output(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    p.wait()
    out = str(p.communicate()[0])
    return out


def cli_error(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
    err = str(p.communicate()[1])
    p.wait()
    return err

def cli_response(argument_string):
    p = subprocess.Popen(argument_string, shell=True, stderr=subprocess.PIPE, universal_newlines=True)
    response = p.communicate()
    p.wait()
    return response

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

def cli_expect(argument_string, expected_list, param_list):
    try:
        child = pexpect.spawn(argument_string)
        for i in range(len(expected_list)):
            child.expect(expected_list[i], timeout=180)
            child.send(param_list[i])
            time.sleep(2)
        return True
    except Exception as e:
        print(f"Exception in cli_expect: {e}")
        return False

def cli_expect_error(argument_string, expected_list, param_list):
    try:
        child = pexpect.spawn(argument_string)
        for i in range(len(expected_list)):
            child.expect(expected_list[i], timeout=180)
            child.send(param_list[i])
            time.sleep(2)
            error_str = child.read().decode('utf-8').split('\r\n')[-2]
        return error_str
    except Exception as e:
        print(f"Exception in cli_expect_error: {e}")
        return None

