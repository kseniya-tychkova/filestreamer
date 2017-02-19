FileStreamer
============

This is a simple web application which allows upload files and calculate the count of characters in uploaded files.

It is written with Flask framework and gevent library.

How To Run Application
======================

To run the web application you should execute the following command:

```
  mkdir /tmp/test
  apt-get install python python-pip
  pip install -r requirements.txt
  python application.py
```

How To Run Tests
================

FileStreamer has unit automated test cases.

To run unit tests you should execute the following command:

```
  pip install -r test-requirements.txt
  nosetests
```

To get information about the test coverage you can use the following command:

```
  nosetests --with-coverage --cover-package=filestreamer
```
