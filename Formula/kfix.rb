class Kfix < Formula
  include Language::Python::Virtualenv

  desc "AI-powered Kubernetes troubleshooter CLI"
  homepage "https://github.com/ilyaselhallaoui/kfix"
  url "https://files.pythonhosted.org/packages/source/k/kfix/kfix-0.3.0.tar.gz"
  # Update sha256 after PyPI release: sha256sum kfix-0.3.0.tar.gz
  sha256 "PLACEHOLDER_UPDATE_AFTER_PYPI_RELEASE"
  license "MIT"

  bottle do
    sha256 cellar: :any_skip_relocation, arm64_sonoma: "PLACEHOLDER"
    sha256 cellar: :any_skip_relocation, ventura:      "PLACEHOLDER"
    sha256 cellar: :any_skip_relocation, x86_64_linux: "PLACEHOLDER"
  end

  depends_on "python@3.12"

  resource "anthropic" do
    url "https://files.pythonhosted.org/packages/source/a/anthropic/anthropic-0.49.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.15.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.9.4.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "tenacity" do
    url "https://files.pythonhosted.org/packages/source/t/tenacity/tenacity-9.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "kfix version 0.3.0", shell_output("#{bin}/kfix version")
    assert_match "diagnose", shell_output("#{bin}/kfix --help")
  end
end
