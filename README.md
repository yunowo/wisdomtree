# wisdomtree
A simple script that makes studying much easier.

## Install
Requires Python 3.6+
 - `git clone https://github.com/yunv/wisdomtree`
 - `pip3 install requests`
 - `pip3 install pycryptodomex`

## Usage
 - Run `study.py` with Python3 (`python study.py` on Windows, `python3 study.py` on Linux and macOS)
 - Enter your phone number and password, `userId` will be saved and you will not need to login again.
 - Press `y` when it found the right course.
 - All lessons will be marked as watched.
 - It will try correct answers out. This feature is considered dangerous and requires to change `TAKE_EXAMS` flag to `True` in `study.py`. If you also want to submit exams automatically, change `EXAM_AUTO_SUBMIT` flag to `True`. Exams that contain short answer questions will not be submitted automatically.

## Notice
### Deprecation of exam submission
As of December 2017, server no longer returns `realAnswer`, so it's impossible to save correct answers directly. You should do exams yourself.

### A brute force method
However, there is an API where we can see scores of every question so a trial-and-error method is implemented. It requires a lot of communication with the server. Use at your own risk.
