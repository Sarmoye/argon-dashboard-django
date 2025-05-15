#!/bin/bash

# Stop Celery Beat
sudo systemctl stop celery-beat.service
sudo systemctl disable celery-beat.service

# Stop Celery Flower
sudo systemctl stop celery-flower.service
sudo systemctl disable celery-flower.service

# Stop Celery workers for each queue
for queue in execute_cis_error_report process_cis_error_report execute_ecw_error_report process_ecw_error_report; do
    sudo systemctl stop celery-worker@$queue.service
    sudo systemctl disable celery-worker@$queue.service
done

echo "All Celery services have been stopped."