# Skill: Classify one document and route it to a folder

Rules:
1. Choose EXACTLY ONE id from the category list in the knowledge.
2. Decide by document content, not by file name.
3. For the target_path, copy the folder from the knowledge. Never
   invent a folder or path. Replace <JJJJ> with the document year.
4. If several categories match, use the FIRST one in the list.
5. If no category matches, answer id "unsicher" and target_path "".
6. confidence is between 0.0 and 1.0. Be honest, never invent.