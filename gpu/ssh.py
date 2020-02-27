import xml.etree.ElementTree

import paramiko


def remove_values_from_list(the_list, val):
    return [value for value in the_list if value != val]


def owner(ssh, pid):
    try:
        # the /proc/PID is owned by process creator
        # pid_query = "ps --pid " + str(pid) + " -u"
        pid_query = "ps --pid {} -o pid,user:20,%cpu,%mem,command --no-headers".format(
            pid)
        # get UID via stat call
        stdin, stdout, stderr = ssh.exec_command(pid_query)
        # look up the username from uid
        pid_out = stdout.read()
        if isinstance(pid_out, bytes):
            pid_out = pid_out.decode()
        pid_out = pid_out.strip().split(" ")
        pid_out = remove_values_from_list(pid_out, "")
        username = pid_out[1].strip()
        command = " "
        for index in range(4, len(pid_out)):
            command += pid_out[index].strip()
            command += " "
    except Exception as e:
        username = 'unknown'
        command = 'unknown'
        print(e)
    return username, command


def get_server_status(hostname, port, username, password):

    ssh = paramiko.SSHClient()

    # known hosts
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # connect to the server
    ssh.connect(hostname=hostname, port=port,
                username=username, password=password)

    # get cpu usage
    cmd = "top -b -d1 -n5|grep -i \"Cpu(s)\""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    cpu_usage_datas = stdout.read()
    cpu_usage_datas = cpu_usage_datas.split("\n")
    cpu_usage_datas.pop()
    cpu_usage = []
    for cpu_usage_data in cpu_usage_datas:
        # print(cpu_usage_data)
        cpu_usage_data = cpu_usage_data[cpu_usage_data.find(
            " ") + 1:cpu_usage_data.find("us") - 1]
        cpu_usage.append(float(cpu_usage_data))
        # print(cpu_usage)
    print("Cpu -usage: %0.2f %%" % max(cpu_usage))
