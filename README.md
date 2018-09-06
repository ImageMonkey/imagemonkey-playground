<img src="https://raw.githubusercontent.com/bbernhard/imagemonkey-core/develop/img/logo.png" align="left" width="180" >


ImageMonkey is a free, public open source dataset. With all the great machine learning frameworks available it's pretty easy to train pre-trained Machine Learning models with your own image dataset. However, in order to do so you need a lot of images. And that's usually the point where it get's tricky. You either have to create the training images yourself or scrape them together from various datasources. ImageMonkey aims to solve this problem, by providing a platform where users can drop their photos, tag them with a label, and put them into public domain.

---
![Alt Text](https://github.com/bbernhard/imagemonkey-core/raw/master/img/animation.gif)

This repository contains the sourcecode of the ImageMonkey Playground. The ImageMonkey Playground is an online image classification service where users can upload photos which then are classified by a ML model trained with the currently available dataset. 

## Base System Configuration ##

* create a new user 'playground` with `adduser playground` 
* disable root login via ssh by changing the `PermitRootLogin` line in `/etc/ssh/sshd_config` to `PermitRootLogin no`)
* block all ports except port 22, 443 and 80 (on eth0) with: 
```
#!bash

iptables -P INPUT DROP && iptables -A INPUT -i eth0 -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -i eth0 -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -i eth0 -p tcp --dport 80 -j ACCEPT
```

* allow all established connections with:

```
#!bash

iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
```

* allow all loopback access with:
```
#!bash
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
```

* install `iptables-persistent` to load firewall rules at startup
* save firewall rules with: `iptables-save > /etc/iptables/rules.v4`
* verify that rules are loaded with `iptables -L`



* install supervisor with `apt-get install supervisor`
* add `imagemonkey` user to supervisor group with `adduser imagemonkey supervisor`
* create logging directories for all the services:
  ```
  mkdir -p /var/log/imagemonkey-playground
  mkdir -p /var/log/imagemonkey-playground-autoannotator
  mkdir -p /var/log/imagemonkey-playground-grabcut
  mkdir -p /var/log/imagemonkey-playground-train
  mkdir -p /var/log/imagemonkey-playground-web
  ```
* copy `conf/supervisor/*` to `/etc/supervisor/conf.d/`
* run `supervisorctl reread && supervisorctl update && supervisorctl restart all

* use `visudo` and add the following entry `playground ALL = (root) NOPASSWD:/usr/bin/supervisorctl restart all` after the line `%sudo   ALL=(ALL:ALL) ALL` to restart supervisord controlled processes with sudo as non-root user

* install `docker`
* make it possible to let users other than root run docker with: 
```

    #Add the docker group if it doesn't already exist.
    sudo groupadd docker
    
    #Add user 'playgroun' to the docker group.
    sudo gpasswd -a playground docker
    
    #Restart the docker daemon.
    sudo service docker restart
    
    #Change owner of the following files
    chown root:docker /var/run/docker.sock
    chown root:docker /usr/bin/docker
```
