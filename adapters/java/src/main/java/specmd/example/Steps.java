package specmd.example;

import io.cucumber.java.pt.Dado;
import io.cucumber.java.pt.Quando;
import io.cucumber.java.pt.Então;

public final class Steps {
    private int a,b,result;
    @Dado("os números {int} e {int}") public void operands(int a,int b){this.a=a;this.b=b;}
    @Quando("a aplicação somar os números") public void sum(){result=Application.add(a,b);}
    @Então("o resultado deve ser {int}") public void check(int expected){
        if(result!=expected)throw new AssertionError("Application.add("+a+","+b+")="+result+"; expected "+expected);
    }
}
