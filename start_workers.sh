#!/bin/bash

# Activate environment
source /etc/nginx/sites-available/argon-dashboard-django/ems_venv/bin/activate

# Start Celery Beat
sudo systemctl enable celery-beat.service
sudo systemctl start celery-beat.service

# Start Celery Flower
sudo systemctl enable celery-flower.service
sudo systemctl start celery-flower.service

# Start Celery workers for each queue
for queue in execute_cis_error_report process_cis_error_report execute_ecw_error_report process_ecw_error_report execute_irm_error_report process_irm_error_report; do
    sudo systemctl enable celery-worker@$queue.service
    sudo systemctl start celery-worker@$queue.service
done

echo "All Celery services have been started."