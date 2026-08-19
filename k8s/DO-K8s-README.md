# DigitalOcean Kubernetes deployment notes

This documents the shape of a DigitalOcean Kubernetes (DOKS) deployment for this
project — no real cluster IDs, IPs, or credentials are included here since this
is a public repo. Fill in your own values as you go.

## What you'll have after setup

- A DOKS cluster (see `k8s/README.md` for the `doctl kubernetes cluster create` command)
- A LoadBalancer (created automatically by the `nginx` Service/Ingress) with its own
  public IPv4/IPv6 — get it with:
  ```bash
  kubectl get service nginx -n podcast-generator -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
  ```
- One or more worker nodes in the node pool you specified at cluster creation
- A managed PostgreSQL database (optional — you can also run Postgres in-cluster via
  `k8s/04-postgres-deployment.yaml`) with its own CA certificate for `sslmode=verify-ca`

## Connecting your domain

Point an A record for your chosen domain (referenced as `K8S_DOMAIN` in
`k8s/02-configmap.yaml` / your `.env`) at the LoadBalancer IP above. `doctl compute
domain records` can automate this — see the `Update DNS Record` step in
`docs/github-workflows/deploy-k8s-DO.yml.example` for a scripted example.

## Managed Postgres CA certificate

If you use DigitalOcean's managed Postgres, download its CA certificate from the
DO control panel and save it locally as `k8s/postgres-ca.crt` (gitignored — never
commit it). Create the cluster secret with:

```bash
kubectl create secret generic postgres-ca -n podcast-generator \
  --from-file=ca.crt=k8s/postgres-ca.crt --dry-run=client -o yaml | kubectl apply -f -
```

## Kubeconfig

`doctl kubernetes cluster kubeconfig save <cluster-name>` writes a kubeconfig
containing your cluster's auth token/CA data. Never commit this file — it's
equivalent to a root credential for the cluster. Keep it in your local
`~/.kube/config` or a secrets manager instead.
