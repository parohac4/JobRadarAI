# Společná část vhostu chcetejelena.cz – vkládá se z :80 i :443 (Include).
# Na serveru: /etc/apache2/sites-available/chcetejelena-common.inc
# Moduly: proxy proxy_http headers rewrite ssl

DocumentRoot /var/www/chcetejelena
<Directory /var/www/chcetejelena>
    Require all granted
    Options -Indexes
    AllowOverride None

    # Repo soubory a skryté soubory se nemají servírovat, i kdyby se do webrootu dostaly
    <FilesMatch "^(\.|README\.md$|LICENSE$|deploy\.sh$)">
        Require all denied
    </FilesMatch>

    # Kontakty se mění bez buildu – config.js necachovat (Cloudflare respektuje no-cache)
    <Files "config.js">
        Header set Cache-Control "no-cache"
    </Files>

    Header set Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'"
</Directory>
RedirectMatch 404 /\.git
ErrorDocument 404 /404.html

Header set X-Content-Type-Options "nosniff"
Header set Referrer-Policy "strict-origin-when-cross-origin"
Header set X-Frame-Options "DENY"
Header set Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()"

ProxyPreserveHost On
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"

RedirectMatch 301 ^/nastenka$ /nastenka/

ProxyPass /nastenka/api/ http://127.0.0.1:8787/api/
ProxyPassReverse /nastenka/api/ http://127.0.0.1:8787/api/

ProxyPass /nastenka/ http://127.0.0.1:8788/
ProxyPassReverse /nastenka/ http://127.0.0.1:8788/

<Location /nastenka/>
    Header set X-Robots-Tag "noindex, nofollow"
</Location>

ErrorLog ${APACHE_LOG_DIR}/chcetejelena-error.log
CustomLog ${APACHE_LOG_DIR}/chcetejelena-access.log combined
