# How to run Medplum (FHIR server) locally.

Clone the repo.  https://github.com/medplum/medplum.

You need a docker implementation.  On a Mac you can use 'colima' (install via Homebrew).  Docker Desktop is an option, but you need a license.

In the Medplum root, run `docker compose up -d`. This will start the Medplum dependencies as daemon (-d) processes - PostgreSQL and Redis.  A Docker volume will be created for persistent storage of the PostgreSQL data.

Then build and start Medplum (server):
```
cd $medplum_repo
npm ci
npm run build:fast
cd packages/server
npm run dev
```

Then start the Medplum console (app, in another window):
```
cd packages/app
MEDPLUM_BASE_URL=http://localhost:8103 npm run dev
```
You can then browse http://localhost:300 and log in (to the console) as Super Admin with `admin@example.com/medplum_admin`.
