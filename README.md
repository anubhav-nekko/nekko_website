Step 0: Initialise Miniconda with: export PATH=~/miniconda3/bin:$PATH

Step 1: Update the default file in: /etc/nginx/sites-available/default

Step 2: Test Config With: sudo nginx -t

Step 3: Reload Nginx server: sudo systemctl reload nginx

Step 4: Clone Repo in /var/www/

Step 5: Install Requirements: pip install -r requirements.txt