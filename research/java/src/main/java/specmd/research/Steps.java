package specmd.research;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public final class Steps {
    private int left;
    private int right;
    private int result;

    @Given("os números {int} e {int}")
    public void numbers(int left, int right) {
        this.left = left;
        this.right = right;
    }

    @When("a aplicação somar os números")
    public void add() {
        result = Application.add(left, right);
    }

    @Then("o resultado deve ser {int}")
    public void result(int expected) {
        if (result != expected) {
            throw new AssertionError("Expected " + expected + " but application returned " + result);
        }
    }
}
