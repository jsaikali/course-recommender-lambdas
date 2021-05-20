# Roster

The code for uploading roster data is in `lambda_function.py`. It needed to be uploaded to Lambda in a zip file containing dependencies, hence the folder "Lambda Upload"

## Lambda setup
### Roles
Open the roles page in the IAM console: https://console.aws.amazon.com/iam/home#/roles  
Create a role with the following permissions:
- AmazonS3FullAccess  
- AWSLambdaBasicExecutionRole  
- AWSLambda_FullAccess     

Call it "lambda-s3-role"  

### Function
Open the Functions page on the Lambda console: https://console.aws.amazon.com/lambda/home#/functions  
Choose Create function.  
Use Python 3.6  
On the Create function page, choose Use a blueprint.  
Under Blueprints, enter s3 in the search box.   
Choose s3-get-object-python.  
Make sure to assign the "lambda-s3-role" to this function.  
I called it "pullCourses"

For testing, make a configuration using this json:
```
{
  "part": "1"
}
```
There will be two separate schedules, for part 1 and part 2.  

### Schedule
Open the Rules page: https://console.aws.amazon.com/events/home?region=us-east-1#/rules
- Create a new rule called "pullCoursesFallPart1" that points to Lambda "pullCourses" with cron schedule `0 4 * 3 ? *` and with JSON constant {"part": "1"}  
Create a new rule called "pullCoursesSpringPart1" that points to Lambda "pullCourses" with cron schedule `0 4 * 10 ? *` and with JSON constant {"part": "1"}  
- Create a new rule called "pullCoursesFallPart2" that points to Lambda "pullCourses" with cron schedule `20 4 * 3 ? *` and with JSON constant {"part": "2"}  
Create a new rule called "pullCoursesSpringPart2" that points to Lambda "pullCourses" with cron schedule `20 4 * 10 ? *` and with JSON constant {"part": "2"}  
- Create a new rule called "pullCoursesFallCombine" that points to Lambda "pullCourses" with cron schedule `45 4 * 3 ? *` and with JSON constant {"part": "3"}  
Create a new rule called "pullCoursesSpringCombine" that points to Lambda "pullCourses" with cron schedule `20 4 * 10 ? *` and with JSON constant {"part": "3"} 

The jobs had to be split up to avoid the 15 minute Lambda limit.

## Download packages and unzip them
These are the dependencies required. Put the unzipped contents the same directory as `lambda_function.py`

pandas:  
https://files.pythonhosted.org/packages/e6/de/a0d3defd8f338eaf53ef716e40ef6d6c277c35d50e09b586e170169cdf0d/pandas-0.24.1-cp36-cp36m-manylinux1_x86_64.whl

numpy:  
https://files.pythonhosted.org/packages/f5/bf/4981bcbee43934f0adb8f764a1e70ab0ee5a448f6505bd04a87a2fda2a8b/numpy-1.16.1-cp36-cp36m-manylinux1_x86_64.whl

pytz:
https://files.pythonhosted.org/packages/70/94/784178ca5dd892a98f113cdd923372024dc04b8d40abe77ca76b5fb90ca6/pytz-2021.1-py2.py3-none-any.whl

requests:
https://files.pythonhosted.org/packages/29/c1/24814557f1d22c56d50280771a17307e6bf87b70727d975fd6b2ce6b014a/requests-2.25.1-py2.py3-none-any.whl

tqdm: 
https://files.pythonhosted.org/packages/72/8a/34efae5cf9924328a8f34eeb2fdaae14c011462d9f0e3fcded48e1266d1c/tqdm-4.60.0-py2.py3-none-any.whl