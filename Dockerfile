FROM python:3.6-slim
COPY . /proj_folder
WORKDIR /proj_folder
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "app.py"]
