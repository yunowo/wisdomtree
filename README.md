# wisdomtree
A simple script that makes studying much easier.

**Warning:** Exam submission is no longer working. You should do exams yourself.

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
 - ~It will save correct answers and submit the exam automatically. Exams that include short answer questions will not be submitted.~

## Notice
### Deprecation of exam submission
As of December 2017, server no longer returns `realAnswer`, so it's impossible to save correct answers. You should do exams yourself. However, before submitting you can check your answer via `getUserAnswerForCheckAnswer` API, where you can see scores of every question.
