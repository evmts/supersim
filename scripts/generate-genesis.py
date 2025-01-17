
import logging
import os
import subprocess
import json
import socket
import time
import shutil
import http.client

log = logging.getLogger()

monorepo_base_path = "lib/optimism"

mnemonic = "supersim supersim supersim supersim supersim supersim supersim supersim supersim supersim supersim junk"

deployer_addresses = [
  "0x07784b280dc6338c03ab1de4dc8033df71a3f80f",
  "0x6d769ea603316f62a0dd39f6d9fb22dc3d7120a3",
  "0x324ef6876f18058cb371c9c8e1caa58cd6566d66",
  "0xa9d4b37e7215fc4678d30ddb719d2e911ec882dd",
  "0x20ae20a11950d9abbc87cf988ca3f8e16e213182",
  "0x6f0b1ec06a67667f7c4e8fdde339a3c5a1a8cd17",
  "0x9a4b16919b2e73f43baf2de63370f1026d30a145",
  "0x6c7579ff19018e29703850ebb171d699792b0041",
  "0xef8ca5b6baab0652528b5acfcc88387a54f6e522",
  "0x2835eed565957fcda0da56df49e7975447e1a037",
]

l1_rpc_port = 8545

class L1:
  def __init__(self, l1_chain_id, supersim_dir):
    self.l1_chain_id = l1_chain_id

    supersim_output_dir = os.path.join(supersim_dir, 'genesis', 'generated')

    self.combined_l1_allocs_path = os.path.join(supersim_output_dir, 'l1-combined-allocs.json')
    self.l1_genesis_path = os.path.join(supersim_output_dir, 'l1-genesis.json')

class L2:
  def __init__(self, l1_chain_id, l2_chain_id, deployer_address, supersim_dir):
    self.l1_chain_id = l1_chain_id
    self.l2_chain_id = l2_chain_id

    self.deployer_address = deployer_address

    supersim_output_dir = os.path.join(supersim_dir, 'genesis', 'generated')

    self.addresses_path = os.path.join(supersim_output_dir, 'addresses', f"{self.l2_chain_id}-addresses.json")
    self.deploy_config_path = os.path.join(supersim_output_dir, 'deploy-configs', f"{self.l2_chain_id}-deploy-config.json")
    self.l1_allocs_path = os.path.join(supersim_output_dir, 'l1-allocs', f"{self.l2_chain_id}-l1-allocs.json")
    self.l2_allocs_path = os.path.join(supersim_output_dir, 'l2-allocs', f"{self.l2_chain_id}-l2-allocs.json")
    self.l2_allocs_with_periphery_path = os.path.join(supersim_output_dir, 'l2-allocs-with-periphery', f"{self.l2_chain_id}-l2-allocs-with-periphery.json")
    self.l2_genesis_path = os.path.join(supersim_output_dir, 'l2-genesis', f"{self.l2_chain_id}-l2-genesis.json")
    self.l2_rollup_config_path = os.path.join(supersim_output_dir, 'rollup-configs', f"{self.l2_chain_id}-rollup-config.json")

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def main():
  supersim_dir = os.path.abspath(os.path.join(os.path.realpath(__file__), '../..'))
  supersim_contracts_dir = os.path.join(supersim_dir, 'contracts')
  supersim_output_dir = os.path.join(supersim_dir, 'genesis', 'generated')
  supersim_output_deploy_configs_dir = os.path.join(supersim_output_dir, "deploy-configs")
  supersim_output_l1_allocs_dir = os.path.join(supersim_output_dir, "l1-allocs")
  supersim_output_addresses_dir = os.path.join(supersim_output_dir, "addresses")
  supersim_output_l2_allocs_dir = os.path.join(supersim_output_dir, "l2-allocs")
  supersim_output_l2_allocs_with_periphery_dir = os.path.join(supersim_output_dir, "l2-allocs-with-periphery")
  supersim_output_l2_genesis_dir = os.path.join(supersim_output_dir, "l2-genesis")
  supersim_output_rollup_dir = os.path.join(supersim_output_dir, "rollup-configs")

  os.makedirs(supersim_output_dir, exist_ok=True)
  os.makedirs(supersim_output_deploy_configs_dir, exist_ok=True)
  os.makedirs(supersim_output_l1_allocs_dir, exist_ok=True)
  os.makedirs(supersim_output_addresses_dir, exist_ok=True)
  os.makedirs(supersim_output_l2_allocs_dir, exist_ok=True)
  os.makedirs(supersim_output_l2_allocs_with_periphery_dir, exist_ok=True)
  os.makedirs(supersim_output_l2_genesis_dir, exist_ok=True)
  os.makedirs(supersim_output_rollup_dir, exist_ok=True)

  monorepo_dir = os.path.abspath(monorepo_base_path)
  monorepo_op_node_dir = os.path.join(monorepo_dir, 'op-node')
  monorepo_contracts_bedrock_dir = os.path.join(monorepo_dir, 'packages', 'contracts-bedrock')
  monorepo_deployment_dir = os.path.join(monorepo_contracts_bedrock_dir, 'deployments')
  monorepo_deploy_config_dir = os.path.join(monorepo_contracts_bedrock_dir, 'deploy-config')
  monorepo_forge_l1_dump_path = os.path.join(monorepo_contracts_bedrock_dir, 'state-dump-900.json')
  monorepo_default_deploy_config_template_path = os.path.join(monorepo_deploy_config_dir, 'devnetL1-template.json')

  paths = Bunch(
    supersim_dir=supersim_dir,
    supersim_contracts_dir=supersim_contracts_dir,

    monorepo_dir=monorepo_dir,
    monorepo_op_node_dir=monorepo_op_node_dir,
    monorepo_contracts_bedrock_dir=monorepo_contracts_bedrock_dir,
    monorepo_deployment_dir=monorepo_deployment_dir,
    monorepo_deploy_config_dir=monorepo_deploy_config_dir,
    monorepo_forge_l1_dump_path=monorepo_forge_l1_dump_path,
    monorepo_default_deploy_config_template_path=monorepo_default_deploy_config_template_path,
  )

  l1_chain_id = 900

  def get_l2_chain(i): 
    return L2(l1_chain_id, 901 + i, deployer_addresses[i], supersim_dir)

  l1_chain = L1(l1_chain_id, supersim_dir)
  l2_chains = list(map(get_l2_chain, range(5)))

  generate_deploy_configs(paths, l2_chains)
  generate_l1_allocs_and_addresses(paths, l2_chains)
  generate_combined_l1_allocs(paths, l1_chain, l2_chains)
  generate_l2_allocs(paths, l2_chains)
  deploy_l2_periphery_contracts(paths, l2_chains)
  generate_l1_genesis(paths, l1_chain, l2_chains)
  generate_l2_genesis(paths, l1_chain, l2_chains)
  
def generate_deploy_configs(paths, l2_chains: list[L2]):
  for l2_chain in l2_chains:
    # Create deploy configs that will be used by the foundry deploy script
    deploy_config = read_json(paths.monorepo_default_deploy_config_template_path)
    deploy_config['l1ChainID'] = l2_chain.l1_chain_id
    deploy_config['l2ChainID'] = l2_chain.l2_chain_id
    deploy_config['useInterop'] = True

    write_json(l2_chain.deploy_config_path, deploy_config)
    

def generate_l1_allocs_and_addresses(paths, l2_chains: list[L2]): 
  for l2_chain in l2_chains:

    # Copy deploy-config.json into monorepo so that the deploy script can use it
    monorepo_deploy_config_path = os.path.join(paths.monorepo_deploy_config_dir, f"{l2_chain.l2_chain_id}-deploy-config.json")
    shutil.copy(src=l2_chain.deploy_config_path, dst=monorepo_deploy_config_path)

    # This is the destination of the addresses.json output of the deploy script
    addresses_temp_dir = os.path.join(paths.monorepo_contracts_bedrock_dir, "deployments", "supersim")
    os.makedirs(addresses_temp_dir, exist_ok=True)
    monorepo_addresses_path = os.path.join(addresses_temp_dir, f"{l2_chain.l2_chain_id}-addresses.json")
  
    fqn = 'scripts/deploy/Deploy.s.sol:Deploy'
    run_command([
        # We need to set the sender here to an account we know the private key of,
        # because the sender ends up being the owner of the ProxyAdmin SAFE
        # (which we need to enable the Custom Gas Token feature).
        'forge', 'script', fqn, "--sig", "runWithStateDump()", "--sender", l2_chain.deployer_address
    ], env={
      'DEPLOYMENT_OUTFILE': monorepo_addresses_path,
      'DEPLOY_CONFIG_PATH': monorepo_deploy_config_path,
    }, cwd=paths.monorepo_contracts_bedrock_dir)

    # Copy artifacts into supersim folders
    shutil.move(src=paths.monorepo_forge_l1_dump_path, dst=l2_chain.l1_allocs_path)
    shutil.move(src=monorepo_addresses_path, dst=l2_chain.addresses_path)


def generate_combined_l1_allocs(paths, l1_chain: L1, l2_chains: list[L2]):
    supersim_l1_allocs_paths = map(lambda l2_chain: "\"" + l2_chain.l1_allocs_path + "\"", l2_chains)

    fqn = 'script/CombineAllocs.s.sol:CombineAllocs'
    run_command([
        'forge', 'script', fqn, "--sig", "run(string[] memory allocsPaths, string memory outputPath)", f"[{','.join(supersim_l1_allocs_paths)}]", l1_chain.combined_l1_allocs_path
    ], cwd=paths.supersim_contracts_dir)


def generate_l2_allocs(paths, l2_chains: list[L2]):
  for l2_chain in l2_chains:

    # Copy deploy-config.json into monorepo so that the deploy script can use it
    monorepo_deploy_config_path = os.path.join(paths.monorepo_deploy_config_dir, f"{l2_chain.l2_chain_id}-deploy-config.json")
    shutil.copy(src=l2_chain.deploy_config_path, dst=monorepo_deploy_config_path)

    # Copy addresses.json into monorepo so that the deploy script can use it
    monorepo_addresses_path = os.path.join(paths.monorepo_deployment_dir, f"{l2_chain.l2_chain_id}-addresses.json")

    shutil.copy(src=l2_chain.addresses_path, dst=monorepo_addresses_path)

    fqn = 'scripts/L2Genesis.s.sol:L2Genesis'
    run_command([
        'forge', 'script', fqn, "--sig", "runWithAllUpgrades()"
    ], env={
      'CONTRACT_ADDRESSES_PATH': monorepo_addresses_path,
      'DEPLOY_CONFIG_PATH': monorepo_deploy_config_path,
    }, cwd=paths.monorepo_contracts_bedrock_dir)

    monorepo_forge_l2_dump_path = os.path.join(paths.monorepo_contracts_bedrock_dir, f'state-dump-{l2_chain.l2_chain_id}-fjord.json')

    # Copy artifacts into supersim folders
    shutil.move(src=monorepo_forge_l2_dump_path, dst=l2_chain.l2_allocs_path)    

def deploy_l2_periphery_contracts(paths, l2_chains: list[L2]):
  for l2_chain in l2_chains:
    fqn = 'script/DeployL2PeripheryContracts.s.sol:DeployL2PeripheryContracts'
    run_command([
        'forge', 'script', fqn, "--sig", "runWithStateDump(string allocsPath, string outputPath)", l2_chain.l2_allocs_path, l2_chain.l2_allocs_with_periphery_path
    ], cwd=paths.supersim_contracts_dir)

def generate_l1_genesis(paths, l1_chain: L1, l2_chains: list[L2]):
  # we can use any of the deploy_configs, all the fields used in this process should be the same between the l2s
  supersim_output_deploy_config_path = l2_chains[0].deploy_config_path

  # this is used for verifying that the addresses have correct allocs on them
  # TODO: validate for all l2s not just one l2
  supersim_output_addresses = l2_chains[0].addresses_path

  run_command([
    'go', 'run', 'cmd/main.go', 'genesis', 'l1',
    '--deploy-config', supersim_output_deploy_config_path,
    '--l1-allocs', l1_chain.combined_l1_allocs_path,
    '--l1-deployments', supersim_output_addresses,
    '--outfile.l1', l1_chain.l1_genesis_path,
  ], cwd=paths.monorepo_op_node_dir)


def generate_l2_genesis(paths, l1_chain: L1, l2_chains: list[L2]):
  # TODO: block-time = 2 is a hack because it attempts to get block 1
  anvil_proc = subprocess.Popen([
    'anvil', '--block-time', '2', '--silent', '--init', l1_chain.l1_genesis_path,
  ], cwd=paths.supersim_dir)
  
  l1_rpc_url = f'127.0.0.1:{l1_rpc_port}'

  wait_up(l1_rpc_port)
  wait_for_rpc_server(l1_rpc_url)

  for l2_chain in l2_chains:
    run_command([
        'go', 'run', 'cmd/main.go', 'genesis', 'l2',
        '--l1-rpc', f'http://{l1_rpc_url}',
        '--deploy-config', l2_chain.deploy_config_path,
        '--l2-allocs', l2_chain.l2_allocs_with_periphery_path,
        '--l1-deployments', l2_chain.addresses_path,
        '--outfile.l2', l2_chain.l2_genesis_path,
        '--outfile.rollup', l2_chain.l2_rollup_config_path
    ], cwd=paths.monorepo_op_node_dir)

  anvil_proc.kill()

def write_json(path, data):
  with open(path, 'w+') as f:
    json.dump(data, f, indent='  ')


def read_json(path):
  with open(path, 'r') as f:
    return json.load(f)

def run_command(args, check=True, shell=False, cwd=None, env=None, timeout=None):
    env = env if env else {}
    return subprocess.run(
        args,
        check=check,
        shell=shell,
        env={
            **os.environ,
            **env
        },
        cwd=cwd,
        timeout=timeout
    )

def wait_up(port, retries=10, wait_secs=1):
    for i in range(0, retries):
        log.info(f'Trying 127.0.0.1:{port}')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', int(port)))
            s.shutdown(2)
            log.info(f'Connected 127.0.0.1:{port}')
            return True
        except Exception:
            time.sleep(wait_secs)

    raise Exception(f'Timed out waiting for port {port}.')


def wait_for_rpc_server(url):
    log.info(f'Waiting for RPC server at {url}')

    headers = {'Content-type': 'application/json'}
    body = '{"id":1, "jsonrpc":"2.0", "method": "eth_chainId", "params":[]}'

    while True:
        try:
            conn = http.client.HTTPConnection(url)
            conn.request('POST', '/', body, headers)
            response = conn.getresponse()
            if response.status < 300:
                log.info(f'RPC server at {url} ready')
                return
        except Exception as e:
            log.info(f'Waiting for RPC server at {url}')
            time.sleep(1)
        finally:
            if conn:
                conn.close()


main()
