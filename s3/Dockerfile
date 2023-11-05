FROM public.ecr.aws/lambda/python:3.10


#Set timezone as Seoul
ENV TZ=Asia/Seoul

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

#Set aws credentials
ARG AWS_REGION_NAME
ENV AWS_REGION_NAME=$AWS_REGION_NAME

ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID

ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

#Copy code
COPY *.py ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler"]