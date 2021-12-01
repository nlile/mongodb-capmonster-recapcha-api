FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

RUN apt update && apt upgrade -y

# set working directory
WORKDIR /app/

# copy dependencies
COPY requirements.txt /app/

# install dependencies
RUN pip install -r requirements.txt

# copy project
COPY ./app /app

# expose port
EXPOSE 5000
EXPOSE 5432

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]