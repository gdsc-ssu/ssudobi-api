FROM public.ecr.aws/lambda/python:3.10

#Set timezone as Seoul
ENV TZ=Asia/Seoul

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

#Copy code
COPY *.py ${LAMBDA_TASK_ROOT}
COPY .env ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler"]