import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import PngIcon from "@/components/valuecell/png-icon";
import { EXCHANGE_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";

export const ExchangeForm = withForm({
  defaultValues: {
    trading_mode: "live" as "live" | "virtual",
    exchange_id: "okx",
    api_key: "",
    secret_key: "",
    passphrase: "",
    wallet_address: "",
    private_key: "",
  },
  render({ form }) {
    return (
      <FieldGroup className="gap-6">
        <form.AppField name="trading_mode">
          {(field) => {
            const isLiveTrading = field.state.value === "live";

            return (
              <>
                <Field>
                  <FieldLabel className="font-medium text-base text-gray-950">
                    Transaction Type
                  </FieldLabel>
                  <RadioGroup
                    value={field.state.value}
                    onValueChange={(value) => {
                      const newMode = value as "live" | "virtual";
                      form.reset();
                      if (newMode === "virtual") {
                        form.setFieldValue("exchange_id", "");
                      }

                      field.handleChange(newMode);
                    }}
                    className="flex items-center gap-6"
                  >
                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="live" id="live" />
                      <Label htmlFor="live" className="text-sm">
                        Live Trading
                      </Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="virtual" id="virtual" />
                      <Label htmlFor="virtual" className="text-sm">
                        Virtual Trading
                      </Label>
                    </div>
                  </RadioGroup>
                </Field>

                {isLiveTrading && (
                  <>
                    <form.Field
                      name="exchange_id"
                      key={form.state.values.trading_mode}
                    >
                      {(field) => (
                        <Field>
                          <FieldLabel className="font-medium text-base text-gray-950">
                            Select Exchange
                          </FieldLabel>
                          <Select
                            value={field.state.value}
                            onValueChange={field.handleChange}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="okx">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.okx} />
                                  OKX
                                </div>
                              </SelectItem>
                              <SelectItem value="binance">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.binance} />
                                  Binance
                                </div>
                              </SelectItem>
                              <SelectItem value="blockchaincom">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.blockchaincom} />
                                  Blockchain.com
                                </div>
                              </SelectItem>
                              <SelectItem value="coinbaseexchange">
                                <div className="flex items-center gap-2">
                                  <PngIcon
                                    src={EXCHANGE_ICONS.coinbaseexchange}
                                  />
                                  Coinbase Exchange
                                </div>
                              </SelectItem>
                              <SelectItem value="gate">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.gate} />
                                  Gate.io
                                </div>
                              </SelectItem>
                              <SelectItem value="hyperliquid">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.hyperliquid} />
                                  Hyperliquid
                                </div>
                              </SelectItem>
                              <SelectItem value="mexc">
                                <div className="flex items-center gap-2">
                                  <PngIcon src={EXCHANGE_ICONS.mexc} />
                                  MEXC
                                </div>
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <FieldError errors={field.state.meta.errors} />
                        </Field>
                      )}
                    </form.Field>

                    {/* Show different fields based on exchange type */}
                    <form.Field name="exchange_id">
                      {(exchangeField) => (
                        <>
                          {exchangeField.state.value === "hyperliquid" ? (
                            <>
                              {/* Hyperliquid: Wallet Address */}
                              <form.Field name="wallet_address">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      Wallet Address
                                    </FieldLabel>
                                    <Input
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter Main Wallet Address (0x...)"
                                    />
                                    <FieldError
                                      errors={field.state.meta.errors}
                                    />
                                  </Field>
                                )}
                              </form.Field>

                              {/* Hyperliquid: Private Key */}
                              <form.Field name="private_key">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      Private Key
                                    </FieldLabel>
                                    <Input
                                      type="password"
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter API Wallet Private Key (0x...)"
                                    />
                                    <FieldError
                                      errors={field.state.meta.errors}
                                    />
                                  </Field>
                                )}
                              </form.Field>
                            </>
                          ) : (
                            <>
                              {/* Standard exchanges: API Key */}
                              <form.Field name="api_key">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      API key
                                    </FieldLabel>
                                    <Input
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter API Key"
                                    />
                                    <FieldError
                                      errors={field.state.meta.errors}
                                    />
                                  </Field>
                                )}
                              </form.Field>

                              {/* Standard exchanges: Secret Key */}
                              <form.Field name="secret_key">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      Secret Key
                                    </FieldLabel>
                                    <Input
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter Secret Key"
                                    />
                                    <FieldError
                                      errors={field.state.meta.errors}
                                    />
                                  </Field>
                                )}
                              </form.Field>
                            </>
                          )}
                        </>
                      )}
                    </form.Field>

                    {/* Passphrase field - only shown for OKX and Coinbase Exchange */}
                    <form.Field name="exchange_id">
                      {(exchangeField) =>
                        (exchangeField.state.value === "okx" ||
                          exchangeField.state.value === "coinbaseexchange") && (
                          <form.Field name="passphrase">
                            {(field) => (
                              <Field>
                                <FieldLabel className="font-medium text-base text-gray-950">
                                  Passphrase
                                </FieldLabel>
                                <Input
                                  value={field.state.value}
                                  onChange={(e) =>
                                    field.handleChange(e.target.value)
                                  }
                                  onBlur={field.handleBlur}
                                  placeholder={`Enter Passphrase (Required for ${exchangeField.state.value === "okx" ? "OKX" : "Coinbase Exchange"})`}
                                />
                                <FieldError errors={field.state.meta.errors} />
                              </Field>
                            )}
                          </form.Field>
                        )
                      }
                    </form.Field>
                  </>
                )}
              </>
            );
          }}
        </form.AppField>
      </FieldGroup>
    );
  },
});
