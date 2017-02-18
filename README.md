FileStreamer
============

This is a simple web application which allows upload files and calculate the count of characters in uploaded files.

It is written with Flask framework and gevent library.

How To Run Application
======================

To run the web application you should execute the following command:

```
  apt-get install python python-pip
  tox -e start_filestreamer
```

How To Run Tests
================

FileStreamer has unit and functional automated test cases.

To run unit tests you shoul execute the following command:

```
  tox -e unit_tests
```

To run functional tests you should execute the following command:

```
  tox -e functional_tests
```
