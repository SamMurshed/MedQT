// This script runs automatically when the Mongo container is created.
// It creates the medqueue_db database and the medqueue_user application user.

const applicationDatabase = db.getSiblingDB("medqueue_db");

applicationDatabase.createUser({
  user: "medqueue_user",
  pwd: "medqueue_password",
  roles: [{ role: "readWrite", db: "medqueue_db" }]
});
