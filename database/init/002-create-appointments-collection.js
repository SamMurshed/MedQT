// Ensure the appointments collection exists in medqueue_db
const applicationDatabase = db.getSiblingDB("medqueue_db");

if (!applicationDatabase.getCollectionNames().includes("appointments")) {
  applicationDatabase.createCollection("appointments");

  // Optional: insert a sample document so the database shows up immediately
  applicationDatabase.appointments.insertOne({
    patientName: "Example Patient",
    doctorName: "Example Doctor",
    symptoms: ["headache"],
    priorityScore: 1,
    predictedWaitMinutes: 15,
    status: "queued",
    createdAt: new Date()
  });
}
