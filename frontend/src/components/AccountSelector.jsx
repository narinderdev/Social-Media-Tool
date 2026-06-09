import { Building2 } from "lucide-react";

function AccountSelector({ accounts, selectedAccount, onChange }) {
  if (accounts.length === 0) {
    return null;
  }

  return (
    <section className="account-switcher">
      <label htmlFor="account-selector">Select account</label>
      <div>
        <Building2 size={15} />
        <select
          id="account-selector"
          value={selectedAccount}
          onChange={(event) => onChange(event.target.value)}
        >
          {accounts.map((account) => (
            <option key={account.key} value={account.key}>
              {account.label}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}

export default AccountSelector;
