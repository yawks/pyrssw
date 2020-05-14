# pyrssw
RSS Wrapper : filter rss items and revamp content




nginx.conf configuration :

```

upstream uwsgicluster {
    server pyrssw:3031;
}

...

location ~ /pyrssw/(?<ndpath>.*) {
    include            uwsgi_params;
    uwsgi_pass         uwsgicluster;

    proxy_redirect off;
    proxy_set_header Host $host;

    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Server $host;
    proxy_set_header X-Original-URI $request_uri;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_pass_request_headers on;
    proxy_set_header Connection "keep-alive";
    proxy_store off;
    proxy_pass http://uwsgicluster/$ndpath$is_args$args;

}
```