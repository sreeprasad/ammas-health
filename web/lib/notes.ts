import { Binary, ClientEncryption, type Db, type Document } from "mongodb";

export type DoctorNote = { note_id: string; date: string; department: string; text: string };

let encryption: ClientEncryption | null = null;

function clientEncryption(db: Db): ClientEncryption {
  const key = process.env.NOTES_MASTER_KEY;
  if (!key) throw new Error("NOTES_MASTER_KEY must be set in .env to read doctor notes");
  encryption ??= new ClientEncryption(db.client, {
    keyVaultNamespace: `${db.databaseName}.__keyvault`,
    kmsProviders: { local: { key: Buffer.from(key, "base64") } },
  });
  return encryption;
}

/** Doctor notes with the note text decrypted client-side; the database only holds ciphertext. */
export async function getNotes(db: Db): Promise<DoctorNote[]> {
  const docs = await db.collection("notes").find({}, { projection: { _id: 0 } }).sort({ date: 1 }).toArray();
  const ce = clientEncryption(db);
  return Promise.all(
    docs.map(async (n: Document) => ({
      note_id: n.note_id,
      date: n.date,
      department: n.department,
      text: n.text_enc instanceof Binary ? String(await ce.decrypt(n.text_enc)) : String(n.text ?? ""),
    })),
  );
}
