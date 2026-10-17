> **Optional, not mandatory:** an event organizer confirmed on Sat Oct 17 that these IBM labs are not required for judging. Treat them as optional inspiration for the NNPA/Granite story only.

# IBM mandatory labs (packet L): runbook

Source: <https://github.com/linuxone-community-cloud/jupyter-lab-ml> (4 notebooks in a prebuilt s390x Jupyter image).
**Run this on a separate L1CC VM, not the demo VM.** The loan notebook loads an IBM Granite LLM, and that plus our app won't fit in 7.8 GB.
First check on Hack2Skill (Resources) which labs count and what proof they want. Until then, run all four.

| Notebook | What it shows | Likely counts as |
|---|---|---|
| `Loan_Approval_Demo.ipynb` | XGBoost risk score + IBM Granite on llama.cpp with **zDNN / NNPA** acceleration, plus BM25 retrieval | **Predictive + Generative** |
| `Churn_Scikit_PyTorch.ipynb` | Random-forest churn model, PMML export | Predictive (multi-model) |
| `Fraud_LSTM_Keras_TF.ipynb` | LSTM fraud detection in Keras/TensorFlow | Predictive (multi-model) |
| `Digit_Class_TensorFlow.ipynb` | MNIST in TensorFlow, ONNX export | Optional |

## 1. Human steps (an agent can't do these)
1. Register at <https://linuxone.cloud.marist.edu/#/register?flag=VM> with event code **SSF2026**, then click the activation email.
2. In the portal: **Virtual Servers → your username → Manage SSH Key Pairs → Import** your public key (e.g. `~/.ssh/id_ed25519.pub`).
3. **Service Catalog → Virtual Servers → Manage Instances → Create**: any name, image **Ubuntu 24.04-Datathon**, your key. Wait for **ACTIVE**.
4. Give the VM's IP to your agent **in chat only**. Never commit it (the repo is public).

## 2. Setup on the VM (agent or human)
```bash
ssh linux1@<LAB_VM_IP>
sudo apt-get update -qq && sudo apt-get install -y -qq docker.io && sudo usermod -aG docker $USER && exit   # re-login for the group
ssh linux1@<LAB_VM_IP>
docker pull registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
mkdir -p ~/shared && chmod a+w ~/shared
docker run --network host --name notebook -v /home/linux1/shared:/home/ibm-user/shared -d \
  registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
docker ps
```
**Don't open port 38888 in the firewall** (the lab README's `iptables` step). The image's default token is published in that README,
so an open port would let anyone run code on the VM. Use a tunnel instead.

## 3. Run the notebooks headless (proof that they ran)
```bash
docker exec notebook bash -lc 'ls; ls ~'                          # find where the .ipynb files live
docker exec -w <notebook dir> notebook bash -lc '
  for nb in Loan_Approval_Demo Churn_Scikit_PyTorch Fraud_LSTM_Keras_TF Digit_Class_TensorFlow; do
    timeout 1800 jupyter nbconvert --to notebook --execute "$nb.ipynb" --output "/home/ibm-user/shared/$nb.executed.ipynb" \
      --ExecutePreprocessor.timeout=1500 > "/home/ibm-user/shared/$nb.log" 2>&1 && echo "$nb OK" || echo "$nb FAILED"
  done'
ls -la ~/shared                                                     # executed notebooks + logs, with outputs
```
Run them one at a time if memory is tight (`free -h`). The loan notebook's first cell prints whether the zDNN library is present.

## 4. Screenshots (human, for the submission)
```bash
ssh -L 38888:localhost:38888 linux1@<LAB_VM_IP>
```
Open <http://localhost:38888>, enter the token, and open each `shared/*.executed.ipynb`. Take screenshots of:
- the zDNN/NNPA check cell
- the Granite recommendation output
- each model's metrics cell
- `docker ps` and `uname -m` in the terminal

Crop out the IP. Submit the proof on Hack2Skill if it's asked for.

## 5. Clean up
```bash
docker rm -f notebook    # when done; keep ~/shared for the proof
```
