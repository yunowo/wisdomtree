from getpass import getpass
import requests

SERVER = 'https://appserver.zhihuishu.com/app-web-service'
SSL_VERIFY = False

if __name__ == '__main__':
    s = requests.Session()
    s.headers.update(
        {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.0; Nexus 5X Build/NRD90S', 'Accept-Encoding': 'gzip'})
    s.cookies.update({'Z_LOCALE': '2'})

    account = input('Account(Phone):')
    password = getpass(prompt='Password:')
    assert account or password

    p = {'mobileVersion': '2.6.9', 'mobileType': 1, 'account': account, 'password': password, 'appType': 1}
    r = s.post(SERVER + '/appserver/base/loginApp', data=p, verify=SSL_VERIFY)
    d = r.json()['rt']
    id = d['id']
    name = d['realName']
    print(name + ' ' + str(id))
    with open('userinfo.py', 'w+') as f:
        f.write('USER = ' + str(id))
    print('Login OK.')
